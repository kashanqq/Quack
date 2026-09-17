"""Task template and issued instance persistence without generation or grading."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    SeenTemplate,
)
from app.db.models import (
    TaskInstance as InstanceRow,
)
from app.db.models import (
    TaskTemplate as TemplateRow,
)
from app.schemas.tasks import TaskInstance, TaskTemplateSpec


async def get_template(
    session: AsyncSession, template_id: str
) -> TaskTemplateSpec | None:
    row = await session.get(TemplateRow, template_id)
    return TaskTemplateSpec.model_validate(row.spec) if row is not None else None


async def list_templates(
    session: AsyncSession, skill_id: str | None = None, exam_id: str | None = None
) -> list[TaskTemplateSpec]:
    query = select(TemplateRow)
    if skill_id is not None:
        query = query.where(TemplateRow.skill_id == skill_id)
    if exam_id is not None:
        query = query.where(TemplateRow.exam_id == exam_id)
    rows = (await session.scalars(query.order_by(TemplateRow.id))).all()
    return [TaskTemplateSpec.model_validate(row.spec) for row in rows]


async def upsert_template(session: AsyncSession, spec: TaskTemplateSpec) -> None:
    values = {
        "id": spec.id,
        "exam_id": spec.exam_id,
        "skill_id": spec.skill_id,
        "type": spec.type,
        "difficulty": spec.difficulty,
        "kind": spec.kind,
        "spec": spec.model_dump(mode="json"),
    }
    row = await session.get(TemplateRow, spec.id)
    if row is None:
        session.add(TemplateRow(**values))
    else:
        for key, value in values.items():
            setattr(row, key, value)
    await session.flush()


async def insert_instance(
    session: AsyncSession, student_id: UUID, inst: TaskInstance
) -> None:
    session.add(
        InstanceRow(
            **inst.model_dump(exclude={"options", "trap_answers", "solution_rendered"}),
            student_id=student_id,
            options=[item.model_dump(mode="json") for item in inst.options],
            trap_answers=[item.model_dump(mode="json") for item in inst.trap_answers],
            solution_rendered=inst.solution_rendered,
        )
    )
    await session.flush()


async def get_instance(
    session: AsyncSession, student_id: UUID, instance_id: UUID
) -> TaskInstance | None:
    row = await session.scalar(
        select(InstanceRow).where(
            InstanceRow.id == instance_id, InstanceRow.student_id == student_id
        )
    )
    if row is None:
        return None
    fields = TaskInstance.model_fields
    return TaskInstance.model_validate({name: getattr(row, name) for name in fields})


async def bump_seen(session: AsyncSession, student_id: UUID, template_id: str) -> None:
    row = await session.get(SeenTemplate, (student_id, template_id))
    now = datetime.now(UTC)
    if row is None:
        session.add(
            SeenTemplate(
                student_id=student_id,
                template_id=template_id,
                n_seen=1,
                last_seen_at=now,
            )
        )
    else:
        row.n_seen += 1
        row.last_seen_at = now
    await session.flush()


async def get_seen(
    session: AsyncSession, student_id: UUID, skill_id: str
) -> dict[str, int]:
    rows = await session.execute(
        select(SeenTemplate.template_id, SeenTemplate.n_seen)
        .join(TemplateRow, TemplateRow.id == SeenTemplate.template_id)
        .where(SeenTemplate.student_id == student_id, TemplateRow.skill_id == skill_id)
    )
    return dict(rows.all())
