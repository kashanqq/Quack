"""B1 task issuing — pick template, generate instance, record event.

I/O layer: reads templates from Postgres, calls pure select/generate,
writes the instance and appends task.issued.

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

import random
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repo import sets as sets_repo
from app.db.repo import tasks as tasks_repo
from app.errors import NotFound, ValidationFailed
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.schemas.events import EventIn, EventType, TaskIssuedPayload
from app.schemas.tasks import (
    OptionOut,
    TaskInstance,
    TaskInstanceOut,
    TaskRequestIn,
)
from app.tasks.generate import generate_instance
from app.tasks.select import pick_template

_logger = structlog.get_logger(__name__)


async def issue(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, req: TaskRequestIn
) -> TaskInstanceOut:
    """Pick a template for the requested skill/set and create one instance."""
    skill_id = await _resolve_skill(session, student_id, req)

    # 1. Шаблоны навыка
    templates_by_skill = await tasks_repo.list_templates_for_skills(session, [skill_id])
    templates = templates_by_skill.get(skill_id, [])
    if not templates:
        raise NotFound(f"no templates for skill {skill_id}")

    # 2. Seen
    seen = await tasks_repo.get_seen_many(session, student_id, [skill_id])

    # 3. Последние грейды навыка — пока недоступно без list_by_skill;
    # передаём пустой список (pick_template берёт медиану сложности)
    last_grades: list[bool] = []

    # 4. Выбор шаблона
    rng = random.Random()
    spec = pick_template(
        templates=templates,
        seen=seen,
        last_grades=last_grades,
        with_trap=req.with_trap,
        other_structure_than=None,
        rng=rng,
    )
    if spec is None:
        raise NotFound(f"no suitable template for skill {skill_id}")

    # 5. Генерация
    seed = rng.randint(1, 10**9)
    instance = generate_instance(spec, seed=seed, student_id=student_id)

    # 6. Запись в БД
    await tasks_repo.insert_instance(session, student_id, instance)

    # 7. Событие task.issued
    via = "topic" if req.mode == "topic" else req.mode
    await events_store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.task_issued,
            payload=TaskIssuedPayload(
                instance_id=instance.id,
                template_id=instance.template_id,
                skill_id=instance.skill_id,
                mode=req.mode,
                via=via,  # type: ignore[arg-type]
            ).model_dump(mode="json"),
            student_id=student_id,
            exam_id=instance.exam_id,
            set_id=req.set_id,
            topic_skill_id=skill_id,
            chat_id=None,
            occurred_at=None,
            extractor_version=None,
            source_event_ids=None,
        ),
    )

    return _to_out(instance, mode=req.mode, provenance=spec.kind)


# --- helpers ---


async def _resolve_skill(
    session: AsyncSession, student_id: UUID, req: TaskRequestIn
) -> str:
    if req.skill_id:
        return req.skill_id
    if req.set_id is not None:
        set_out = await sets_repo.get_set(session, student_id, req.set_id)
        if set_out is None:
            raise NotFound("set not found")
        for topic in set_out.topics:
            if topic.status == "open":
                return topic.skill_id
        raise ValidationFailed("set has no open topics")
    raise ValidationFailed("either skill_id or set_id required")


def _to_out(instance: TaskInstance, *, mode: str, provenance: str) -> TaskInstanceOut:
    return TaskInstanceOut(
        id=instance.id,
        template_id=instance.template_id,
        exam_id=instance.exam_id,
        type=instance.type,
        skill_id=instance.skill_id,
        stem_rendered=instance.stem_rendered,
        options=[OptionOut(key=o.key, text=o.text) for o in instance.options],
        figure_url=instance.figure_url,
        time_reference_sec=instance.time_reference_sec,
        difficulty=instance.difficulty,
        tags=instance.tags,
        mode=mode,  # type: ignore[arg-type]
        provenance=provenance,  # type: ignore[arg-type]
    )
