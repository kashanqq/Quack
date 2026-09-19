"""Pace and the four variants, with the Redis cache in front (§8.3).

`GET /quack` is the one place phase 4 does real arithmetic inside a request.
It is cheap — four to twenty forecasts over at most forty-five skills — but
it needs the states from the graph, so the whole `PaceOut` is cached by the
student's last event id: nothing they did changed, nothing to recompute.
"""

from __future__ import annotations

import json
from datetime import date
from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app import keys
from app.apply.targets import p_target_for
from app.db.repo import aggregates as aggregates_repo
from app.db.repo import forecast as forecast_repo
from app.db.repo import profiles as profiles_repo
from app.db.repo import programs as programs_repo
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import kb as kb_q
from app.graph.queries import personal as personal_q
from app.roadmap.requirements import build_requirements
from app.schemas.common import ExamId
from app.schemas.quack import ExamPaceOut, PaceOut
from app.sets.pace import PaceInputs, base_forecast, variants, words

_logger = structlog.get_logger(__name__)

_PACE_TTL_S = 600


async def compute_all(
    session: AsyncSession, deps: RuleDeps, student_id: UUID
) -> PaceOut:
    """Cached pace for every exam the student's saved programs demand."""
    as_of = await events_store.last_event_id(session, student_id)
    cached = await _read_cache(deps, student_id, as_of)
    if cached is not None:
        return cached

    saved = await programs_repo.list_saved_programs(session, student_id)
    exam_ids: list[ExamId] = sorted(
        {
            requirement.exam_id
            for program in saved
            for requirement in program.requirements
            if requirement.exam_id is not None
        }
    )
    result = PaceOut(
        exams=[
            await compute(session, deps, student_id, exam_id) for exam_id in exam_ids
        ],
        as_of=deps.now(),
    )
    await _write_cache(deps, student_id, as_of, result)
    return result


async def compute(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, exam_id: ExamId
) -> ExamPaceOut:
    """One exam: the base forecast, the four variants and one sentence."""
    profile = await profiles_repo.get_profile(session, student_id)
    saved = await programs_repo.list_saved_programs(session, student_id)
    hours = profile.questionnaire.pace.hours_per_week.value
    summary = await aggregates_repo.get_summary(session, student_id)

    inputs, requirement_target = await _inputs(
        session, deps, student_id, exam_id, profile, saved, hours or 0
    )
    if inputs is None:
        cached = await forecast_repo.get(session, student_id, exam_id)
        return ExamPaceOut(
            exam_id=exam_id,
            forecast=cached,
            on_track=cached.on_track if cached else None,
            test_date=cached.test_date if cached else None,
            hours_declared=hours,
            hours_actual=summary.hours_per_week_actual if summary else None,
            variants=[],
            words=words(
                ExamPaceOut(
                    exam_id=exam_id,
                    forecast=cached,
                    on_track=cached.on_track if cached else None,
                    test_date=cached.test_date if cached else None,
                    hours_declared=hours,
                )
            ),
        )
    del requirement_target

    today = deps.now().date()
    base = base_forecast(inputs, deps.params, today)
    if base is None:
        base = await forecast_repo.get(session, student_id, exam_id)
    pace = ExamPaceOut(
        exam_id=exam_id,
        forecast=base,
        on_track=base.on_track if base else None,
        test_date=inputs.test_date,
        hours_declared=hours,
        hours_actual=summary.hours_per_week_actual if summary else None,
        variants=variants(base, inputs, deps.params, today) if base else [],
    )
    return pace.model_copy(update={"words": words(pace)})


async def _inputs(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    exam_id: ExamId,
    profile,
    saved,
    hours: int,
) -> tuple[PaceInputs | None, float | None]:
    if deps.graph is None:
        return None, None
    try:
        skill_weights = await canonical_q.list_exam_skills(deps.graph, exam_id)
        exam_format = await canonical_q.get_exam_format(deps.graph, exam_id)
        calendar = await kb_q.list_test_dates(deps.graph, exam_id)
        states = await personal_q.get_states(deps.graph, student_id, exam_id)
    except (ServiceUnavailable, SessionExpired):
        _logger.warning("pace_graph_unavailable", student_id=str(student_id))
        return None, None
    if exam_format is None:
        return None, None

    requirements = build_requirements(
        saved=saved,
        profile=profile,
        exam_formats={exam_id: exam_format},
        test_dates={exam_id: calendar},
        forecasts={exam_id: await forecast_repo.get(session, student_id, exam_id)},
        params=deps.params,
    )
    requirement = next((item for item in requirements if item.exam_id == exam_id), None)
    today = deps.now().date()
    test_date = _planned_date(profile, exam_id, requirement, calendar, today)

    return (
        PaceInputs(
            exam_id=exam_id,
            states=states,
            skill_weights=skill_weights,
            exam_format=exam_format,
            effort={item.skill.id: item.skill.effort_h for item in skill_weights},
            p_target=await p_target_for(
                session, deps, student_id, exam_id, exam_format=exam_format
            ),
            hours_per_week=hours,
            test_date=test_date,
            calendar=calendar,
            saved=saved,
            target_score=requirement.target_score if requirement else None,
            max_raw_score=exam_format.max_raw_score,
        ),
        requirement.target_score if requirement else None,
    )


def _planned_date(profile, exam_id: ExamId, requirement, calendar, today: date):
    """The date the student declared, or the first one in the calendar."""
    academics = profile.questionnaire.academics
    field = academics.sat_date if exam_id == "SAT_MATH" else academics.ent_date
    if field.mark == "stated" and field.value is not None:
        return field.value
    if requirement is not None and requirement.test_dates:
        upcoming = [item.date for item in requirement.test_dates if item.date >= today]
        if upcoming:
            return min(upcoming)
    upcoming = [item.date for item in calendar if item.date >= today]
    return min(upcoming) if upcoming else None


# --- cache ---


async def _read_cache(deps: RuleDeps, student_id: UUID, as_of: int) -> PaceOut | None:
    try:
        raw = await deps.redis.get(keys.pace(str(student_id)))
    except (RedisError, OSError):
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        if int(payload.get("as_of_event_id", -1)) != as_of:
            return None
        return PaceOut.model_validate(payload["pace"])
    except (ValueError, KeyError, TypeError):
        return None


async def _write_cache(
    deps: RuleDeps, student_id: UUID, as_of: int, value: PaceOut
) -> None:
    try:
        await deps.redis.set(
            keys.pace(str(student_id)),
            json.dumps(
                {"as_of_event_id": as_of, "pace": value.model_dump(mode="json")}
            ),
            ex=_PACE_TTL_S,
        )
    except (RedisError, OSError):
        _logger.info("pace_cache_unavailable", student_id=str(student_id))
