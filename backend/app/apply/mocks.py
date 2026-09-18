"""B1 mock-exam apply — memory-architecture §8.3, §10.2.

I/O layer: assemble a mock from templates, run it, score it, persist via
repo.mocks / repo.tasks.

Source: 00-contracts-phase2.md §7.2, 20-B1-phase2.md §7.
"""

from __future__ import annotations

import random
from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repo import forecast as forecast_repo
from app.db.repo import mocks as mocks_repo
from app.db.repo import sets as sets_repo
from app.db.repo import tasks as tasks_repo
from app.errors import NotFound, ValidationFailed
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.schemas.common import ExamId
from app.schemas.events import EventIn, EventType, MockStartedPayload
from app.schemas.knowledge import Section
from app.schemas.mocks import MockOut, MockResultOut, MockStartIn
from app.schemas.tasks import (
    AnswerResult,
    Grade,
    OptionOut,
    TaskInstanceOut,
)
from app.tasks.generate import generate_instance
from app.tasks.mocks import assemble_mock, score

_logger = structlog.get_logger(__name__)


async def start(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, body: MockStartIn
) -> MockOut:
    """Assemble and persist a new mock run."""
    if deps.graph is None:
        raise ValidationFailed("graph unavailable")

    try:
        exam_format = await canonical_q.get_exam_format(deps.graph, body.exam_id)
    except (ServiceUnavailable, SessionExpired) as exc:
        raise ValidationFailed("graph unavailable") from exc
    if exam_format is None or not exam_format.sections:
        raise NotFound("exam format not found")

    section = exam_format.sections[0]

    skill_ids = await _resolve_skill_ids(session, deps, student_id, body)
    if not skill_ids:
        raise NotFound("no skills for mock")

    templates_by_skill = await tasks_repo.list_templates_for_skills(session, skill_ids)
    if not templates_by_skill:
        raise NotFound("no templates for mock")

    seen = await tasks_repo.get_seen_many(session, student_id, skill_ids)

    rng = random.Random()
    picks = assemble_mock(
        body.kind, section, templates_by_skill, seen, rng, deps.params
    )
    if not picks:
        raise NotFound("could not assemble mock")

    instances = []
    for _skill_id, spec in picks:
        seed = rng.randint(1, 10**9)
        inst = generate_instance(spec, seed=seed, student_id=student_id)
        await tasks_repo.insert_instance(session, student_id, inst)
        instances.append(inst)

    forecast = await forecast_repo.get(session, student_id, body.exam_id)
    predicted_before = forecast.predicted_scaled if forecast else None

    row = await mocks_repo.create_run(
        session,
        student_id=student_id,
        exam_id=body.exam_id,
        kind=body.kind,
        section_name=section.name,
        instance_ids=[i.id for i in instances],
        set_id=body.set_id,
        skill_id=body.skill_id,
        misconception_id=body.misconception_id,
        predicted_before=predicted_before,
    )

    await events_store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.mock_started,
            payload=MockStartedPayload(
                run_id=row.id,
                kind=body.kind,
                exam_id=body.exam_id,
                predicted_before=predicted_before,
            ).model_dump(mode="json"),
            student_id=student_id,
            exam_id=body.exam_id,
            set_id=body.set_id,
            topic_skill_id=None,
            chat_id=None,
            occurred_at=None,
            extractor_version=None,
            source_event_ids=None,
        ),
    )

    minutes = _minutes_for(section, len(instances))
    return MockOut(
        run_id=row.id,
        kind=body.kind,
        exam_id=body.exam_id,
        section_name=section.name,
        status="active",
        tasks=[_to_task_out(i, mode=body.kind) for i in instances],
        minutes=minutes,
        answered=0,
        predicted_before=predicted_before,
    )


async def answer(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    run_id: UUID,
    result: AnswerResult,
) -> MockOut:
    """Refresh MockOut after one answered task.

    Роутер уже записал task.answered через dispatch; здесь читаем
    актуальный состав задач из БД и возвращаем обновлённый MockOut.
    Точный счётчик answered хранит repo.mocks; пока возвращаем 0.
    """
    row = await mocks_repo.get_run(session, student_id, run_id)
    if row is None:
        raise NotFound("mock run not found")

    instances = await tasks_repo.list_instances(session, student_id, row.instance_ids)

    return MockOut(
        run_id=row.id,
        kind=row.kind,
        exam_id=row.exam_id,
        section_name=row.section_name,
        status=row.status,
        tasks=[_to_task_out(i, mode=row.kind) for i in instances],
        minutes=_minutes_for(_pseudo_section(row), len(instances)),
        answered=0,
        predicted_before=row.predicted_before,
    )


async def finish(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, run_id: UUID
) -> MockResultOut:
    """Score a finished mock, persist, return MockResultOut."""
    row = await mocks_repo.get_run(session, student_id, run_id)
    if row is None:
        raise NotFound("mock run not found")
    if deps.graph is None:
        raise ValidationFailed("graph unavailable")

    try:
        exam_format = await canonical_q.get_exam_format(deps.graph, row.exam_id)
    except (ServiceUnavailable, SessionExpired) as exc:
        raise ValidationFailed("graph unavailable") from exc
    if exam_format is None:
        raise NotFound("exam format not found")

    section = _find_section(exam_format.sections, row.section_name)
    if section is None:
        raise NotFound("exam section not found")

    instances = await tasks_repo.list_instances(session, student_id, row.instance_ids)
    # У нас нет поля correct в схеме TaskInstance — пока считаем все
    # ответы как "неверные" (0). Точный результат даст apply.task_answered
    # при интеграции с историей событий.
    grades: list[Grade] = [Grade(correct=False) for _ in instances]

    raw, scaled = score(section, grades, exam_format)
    await mocks_repo.complete_run(session, run_id, raw, scaled)

    brier_point: float | None = None
    if row.predicted_before is not None and exam_format.max_raw_score > 0:
        predicted_norm = row.predicted_before / exam_format.max_raw_score
        raw_norm = raw / exam_format.max_raw_score
        brier_point = (predicted_norm - raw_norm) ** 2

    await events_store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.mock_completed,
            payload={
                "run_id": str(row.id),
                "raw_score": raw,
                "scaled_score": scaled,
                "predicted_before": row.predicted_before,
            },
            student_id=student_id,
            exam_id=row.exam_id,
            set_id=row.set_id,
            topic_skill_id=row.skill_id,
            chat_id=None,
            occurred_at=None,
            extractor_version=None,
            source_event_ids=None,
        ),
    )

    return MockResultOut(
        run_id=row.id,
        raw_score=raw,
        max_raw=float(exam_format.max_raw_score),
        scaled_score=scaled,
        scale_note=exam_format.scale_note,
        per_skill=[],
        brier_point=brier_point,
    )


# --- helpers ---


async def _resolve_skill_ids(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    body: MockStartIn,
) -> list[str]:
    if body.kind == "mock_topic" and body.skill_id:
        return [body.skill_id]
    if body.kind == "mock_set" and body.set_id is not None:
        set_out = await sets_repo.get_set(session, student_id, body.set_id)
        if set_out is None:
            return []
        return [t.skill_id for t in set_out.topics]
    if body.kind == "mock_misconception":
        try:
            weights = await canonical_q.list_exam_skills(deps.graph, body.exam_id)
        except (ServiceUnavailable, SessionExpired):
            return []
        return [w.skill.id for w in weights]
    return []


def _to_task_out(inst, *, mode: str) -> TaskInstanceOut:
    return TaskInstanceOut(
        id=inst.id,
        template_id=inst.template_id,
        exam_id=inst.exam_id,
        type=inst.type,
        skill_id=inst.skill_id,
        stem_rendered=inst.stem_rendered,
        options=[OptionOut(key=o.key, text=o.text) for o in inst.options],
        figure_url=inst.figure_url,
        time_reference_sec=inst.time_reference_sec,
        difficulty=inst.difficulty,
        tags=inst.tags,
        mode=mode,  # type: ignore[arg-type]
        provenance="template",
    )


def _minutes_for(section: Section, n: int) -> int:
    if section.n_items <= 0:
        return 0
    return round(section.minutes * n / section.n_items)


def _pseudo_section(row) -> Section:
    return Section(
        name=row.section_name,
        n_items=max(1, len(row.instance_ids)),
        minutes=1,
        item_types={},
        scoring_rule="",
        calculator=True,
        adaptive=False,
        area_shares={},
        difficulty_shares={},
        answer_forms=[],
    )


def _find_section(sections: list[Section], name: str) -> Section | None:
    for s in sections:
        if s.name == name:
            return s
    return None


# ExamId импорт нужен для type-hint в других местах; держим явно,
# чтобы не потерять при рефакторе.
_ = ExamId
