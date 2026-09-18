"""Task template and issued instance persistence without generation or grading."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
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
    session: AsyncSession,
    student_id: UUID,
    inst: TaskInstance,
    *,
    mode: str | None = None,
    issued_event_id: int | None = None,
) -> None:
    """Persist one generated instance.

    ``mode`` and ``issued_event_id`` are stored here, not patched afterwards:
    the answer route reads ``mode`` back to validate the answer against the
    mode the task was issued in, and ``issued_event_id`` is what ties the
    instance to its ``task.issued`` event (the observer window and
    `explain_belief` walk that link).
    """
    session.add(
        InstanceRow(
            **inst.model_dump(exclude={"options", "trap_answers", "solution_rendered"}),
            student_id=student_id,
            options=[item.model_dump(mode="json") for item in inst.options],
            trap_answers=[item.model_dump(mode="json") for item in inst.trap_answers],
            solution_rendered=inst.solution_rendered,
            mode=mode,
            issued_event_id=issued_event_id,
        )
    )
    await session.flush()


async def get_answered_at(session: AsyncSession, instance_id: UUID) -> datetime | None:
    """When this instance was answered, or None — the replay guard of §8.2."""
    return await session.scalar(
        select(InstanceRow.answered_at).where(InstanceRow.id == instance_id)
    )


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


async def list_templates_for_skills(
    session: AsyncSession, skill_ids: list[str]
) -> dict[str, list[TaskTemplateSpec]]:
    if not skill_ids:
        return {}
    rows = (
        await session.scalars(
            select(TemplateRow)
            .where(TemplateRow.skill_id.in_(skill_ids))
            .order_by(TemplateRow.skill_id, TemplateRow.id)
        )
    ).all()
    grouped: dict[str, list[TaskTemplateSpec]] = {}
    for row in rows:
        grouped.setdefault(row.skill_id, []).append(
            TaskTemplateSpec.model_validate(row.spec)
        )
    return grouped


async def get_seen_many(
    session: AsyncSession, student_id: UUID, skill_ids: list[str]
) -> dict[str, int]:
    if not skill_ids:
        return {}
    rows = await session.execute(
        select(SeenTemplate.template_id, SeenTemplate.n_seen)
        .join(TemplateRow, TemplateRow.id == SeenTemplate.template_id)
        .where(
            SeenTemplate.student_id == student_id,
            TemplateRow.skill_id.in_(skill_ids),
        )
    )
    return dict(rows.all())


async def mark_answered(
    session: AsyncSession,
    instance_id: UUID,
    answered_at: datetime,
    correct: bool,
) -> None:
    await session.execute(
        update(InstanceRow)
        .where(InstanceRow.id == instance_id)
        .values(answered_at=answered_at, correct=correct)
    )
    await session.flush()


async def last_grades_for_skill(
    session: AsyncSession, student_id: UUID, skill_id: str, limit: int = 2
) -> list[bool]:
    """Last answered grades for one skill, oldest first — input to `pick_template`."""
    rows = (
        await session.scalars(
            select(InstanceRow.correct)
            .where(
                InstanceRow.student_id == student_id,
                InstanceRow.skill_id == skill_id,
                InstanceRow.answered_at.is_not(None),
                InstanceRow.correct.is_not(None),
            )
            .order_by(InstanceRow.answered_at.desc())
            .limit(limit)
        )
    ).all()
    return [bool(value) for value in reversed(rows)]


async def list_instances(
    session: AsyncSession, student_id: UUID, ids: list[UUID]
) -> list[TaskInstance]:
    if not ids:
        return []
    rows = (
        await session.scalars(
            select(InstanceRow).where(
                InstanceRow.student_id == student_id, InstanceRow.id.in_(ids)
            )
        )
    ).all()
    fields = TaskInstance.model_fields
    by_id = {
        row.id: TaskInstance.model_validate(
            {name: getattr(row, name) for name in fields}
        )
        for row in rows
    }
    return [by_id[instance_id] for instance_id in ids if instance_id in by_id]
