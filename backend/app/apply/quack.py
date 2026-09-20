"""Quack: collecting the feed inputs, running the batch, applying a decision.

§8.2 and §8.4. Accepting a recommendation writes the *ordinary* event the
student would have written by hand — `profile.updated`, `program.removed`,
`set.opened` — so the phase-2 rules fire exactly as if they had done it
themselves (product-logic §6.1). Quack never has a private path into the
knowledge model.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app import keys
from app.apply import matching as apply_matching
from app.apply import pace as apply_pace
from app.apply import sets as apply_sets
from app.db.repo import aggregates as aggregates_repo
from app.db.repo import forecast as forecast_repo
from app.db.repo import milestones as milestones_repo
from app.db.repo import profiles as profiles_repo
from app.db.repo import programs as programs_repo
from app.db.repo import recommendations as recs_repo
from app.db.repo import sets as sets_repo
from app.errors import Conflict
from app.events import store as events_store
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import kb as kb_q
from app.quack.plan import PlanInputs, plan
from app.roadmap import conflicts as conflict_rules
from app.roadmap import milestones as milestone_rules
from app.roadmap import requirements as requirement_rules
from app.schemas.common import ExamId
from app.schemas.events import (
    Event,
    EventIn,
    EventType,
    ProfileUpdatedPayload,
    ProgramSavedPayload,
    RecommendationAcceptedPayload,
    RecommendationDeclinedPayload,
    SetDeadlineChangedPayload,
    SetOpenedPayload,
)
from app.schemas.profile import ProfileUpdateIn
from app.schemas.quack import BatchResult, RecommendationAction, RecommendationOut
from app.schemas.sets import SetsByExam

_logger = structlog.get_logger(__name__)

_LOCK_TTL_S = 120
_URGENT_DEBOUNCE_S = 5
_ALL_EXAMS: tuple[ExamId, ...] = ("SAT_MATH", "ENT_MATH")

# Поля анкеты, правка которых меняет состав кандидатов подборки (§0.2).
_SOFT_MATCH_PREFIXES = (
    "traits.summary",
    "preferences.",
    "constraints.",
    "academics.",
    "direction.",
)
# Правки, из-за которых прогноз и сроки надо пересчитать срочно.
_URGENT_PROFILE_FIELDS = (
    "pace.hours_per_week",
    "academics.sat_date",
    "academics.ent_date",
    "academics.sat_target",
    "academics.ent_target",
)


class BatchLocked(Exception):
    """Another batch for this student is already running (§16 item 9б)."""


# --- inputs ---


async def collect_inputs(
    session: AsyncSession, deps: RuleDeps, student_id: UUID
) -> PlanInputs:
    """Everything the pure planner needs, read once (§8.2)."""
    today = deps.now().date()
    profile = await profiles_repo.get_profile(session, student_id)
    saved = await programs_repo.list_saved_programs(session, student_id)

    exam_ids: list[ExamId] = sorted(
        {
            requirement.exam_id
            for program in saved
            for requirement in program.requirements
            if requirement.exam_id is not None
        }
    )
    formats: dict[ExamId, Any] = {}
    test_dates: dict[ExamId, list] = {}
    forecasts = {}
    for exam_id in exam_ids:
        if deps.graph is not None:
            try:
                exam_format = await canonical_q.get_exam_format(deps.graph, exam_id)
                if exam_format is not None:
                    formats[exam_id] = exam_format
                test_dates[exam_id] = await kb_q.list_test_dates(deps.graph, exam_id)
            except (ServiceUnavailable, SessionExpired):
                _logger.warning("quack_graph_unavailable", student_id=str(student_id))
                test_dates[exam_id] = []
        else:
            test_dates[exam_id] = []
        cached = await forecast_repo.get(session, student_id, exam_id)
        if cached is not None:
            forecasts[str(exam_id)] = cached

    requirements = requirement_rules.build_requirements(
        saved,
        profile,
        formats,
        test_dates,
        {exam_id: forecasts.get(str(exam_id)) for exam_id in exam_ids},
        deps.params,
    )
    marks = await milestones_repo.list_marks(session, student_id)
    calendar = [item for dates in test_dates.values() for item in dates]
    milestones = milestone_rules.build_milestones(
        saved, requirements, test_dates, calendar, marks, today
    )
    planned = {
        exam_id: next((item.date for item in dates if item.date >= today), None)
        for exam_id, dates in test_dates.items()
    }
    conflicts = conflict_rules.find_conflicts(milestones, saved, planned)

    pace = await apply_pace.compute_all(session, deps, student_id)
    pace_variants = {item.exam_id: item.variants for item in pace.exams}

    sets_by_exam: dict[str, SetsByExam] = {}
    for exam_id in _ALL_EXAMS:
        items = await sets_repo.list_sets(session, student_id, exam_id)
        if not items:
            continue
        sets_by_exam[str(exam_id)] = SetsByExam(
            exam_id=exam_id,
            forecast=forecasts.get(str(exam_id)),
            current=next((i for i in items if i.status == "current"), None),
            upcoming=[i for i in items if i.status == "upcoming"],
            done=[i for i in items if i.status == "done"],
        )

    matching = await apply_matching.run_matching(session, deps, student_id, limit=10)
    snapshot = await _read_batch_key(deps, student_id)

    return PlanInputs(
        today=today,
        profile=profile,
        saved=saved,
        requirements=requirements,
        milestones=milestones,
        conflicts=conflicts,
        forecasts=forecasts,
        pace_variants={str(k): v for k, v in pace_variants.items()},
        sets_by_exam=sets_by_exam,
        matching_now=matching.items,
        matching_prev=snapshot.get("realism_by_program"),
        aggregates=await aggregates_repo.get_summary(session, student_id),
        open_recs=await recs_repo.list_open(session, student_id, now=deps.now()),
        declined_hashes=await recs_repo.declined_hashes(
            session,
            student_id,
            deps.params.declined_window_days,
            now=deps.now(),
        ),
        previous_upcoming=snapshot.get("upcoming_by_exam") or {},
    )


# --- the batch ---


async def run_batch(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, urgent: bool
) -> BatchResult:
    """Plan, reconcile, and record the portion the student has not seen."""
    lock = keys.lock(f"recs:{student_id}")
    token = uuid4().hex
    if not await _acquire(deps, lock, token):
        raise BatchLocked(str(student_id))
    try:
        inputs = await collect_inputs(session, deps, student_id)
        drafts = plan(inputs, deps.params, inputs.today)
        batch_id = uuid4()
        result = await recs_repo.reconcile(
            session,
            student_id,
            drafts,
            urgent_only=urgent,
            now=deps.now(),
            batch_id=batch_id,
        )
        new_urgent = (
            sum(1 for draft in drafts if draft.urgency == "urgent") if urgent else 0
        )
        # Порция фиксируется кроном всегда, а urgent-запуском — только если
        # он создал хоть одну срочную: срочные выходят сразу (§8.2).
        if not urgent or (result.created and new_urgent):
            await _write_batch_key(deps, student_id, batch_id, result.created, inputs)
        return result
    finally:
        await _release(deps, lock, token)


async def _read_batch_key(deps: RuleDeps, student_id: UUID) -> dict[str, Any]:
    try:
        raw = await deps.redis.get(keys.quack_batch(str(student_id)))
    except (RedisError, OSError):
        return {}
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


async def _write_batch_key(
    deps: RuleDeps,
    student_id: UUID,
    batch_id: UUID,
    n_new: int,
    inputs: PlanInputs,
) -> None:
    payload = {
        "batch_id": str(batch_id),
        "at": deps.now().isoformat(),
        "n_new": n_new,
        # Снапшот для следующего батча: «что было» у «стали подходить» и
        # «состав сета изменился» берётся отсюда, а не из второго прогона.
        "realism_by_program": [
            {"program_id": item.program.id, "realism": item.realism}
            for item in inputs.matching_now
        ],
        "upcoming_by_exam": {
            exam_id: sorted(topic.skill_id for topic in sets.upcoming[0].topics)
            for exam_id, sets in inputs.sets_by_exam.items()
            if sets.upcoming
        },
    }
    try:
        await deps.redis.set(keys.quack_batch(str(student_id)), json.dumps(payload))
    except (RedisError, OSError):
        _logger.info("quack_batch_key_unavailable", student_id=str(student_id))


async def batch_state(deps: RuleDeps, student_id: UUID) -> dict[str, Any]:
    """`new_batch` / `batch_at` / `n_new` of `GET /quack`."""
    return await _read_batch_key(deps, student_id)


async def _acquire(deps: RuleDeps, key: str, token: str) -> bool:
    try:
        return bool(await deps.redis.set(key, token, nx=True, ex=_LOCK_TTL_S))
    except (RedisError, OSError):
        # Redis недоступен — лок считается свободным (§2.3): дубликаты
        # отсекает частичный уникальный индекс по (student_id, reason_hash).
        _logger.warning("lock_redis_unavailable", key=key)
        return True


async def _release(deps: RuleDeps, key: str, token: str) -> None:
    try:
        current = await deps.redis.get(key)
        if current is not None:
            value = current.decode() if isinstance(current, bytes) else current
            if value == token:
                await deps.redis.delete(key)
    except (RedisError, OSError):
        return


# --- decisions (§8.4) ---


async def apply_accept(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> RecommendationOut | None:
    """Turn an accepted recommendation into the event it stands for."""
    if event.type != EventType.recommendation_accepted:
        return None
    payload = RecommendationAcceptedPayload.model_validate(event.payload)
    row = await recs_repo.get(session, event.student_id, payload.recommendation_id)
    if row is None:
        return None
    if row.status == "accepted":
        # Повтор: ничего не пишем второй раз (§11 «повторная доставка»).
        return row
    if row.status in ("declined", "expired"):
        raise Conflict("recommendation already decided")

    if not await _still_actionable(session, event.student_id, row.action):
        await recs_repo.decide(
            session,
            event.student_id,
            row.id,
            "expired",
            now=deps.now(),
            decision_event_id=event.id,
        )
        raise Conflict("stale_recommendation")

    await _perform(session, event, deps, row.action)
    updated = await recs_repo.decide(
        session,
        event.student_id,
        row.id,
        "accepted",
        now=deps.now(),
        decision_event_id=event.id,
    )
    if row.kind == "pace_variant":
        # Принятый вариант темпа снимает остальные варианты того же экзамена.
        await recs_repo.expire_siblings(
            session,
            event.student_id,
            "pace_variant",
            row.exam_id,
            keep_id=row.id,
            now=deps.now(),
        )
    deps.jobs.enqueue(
        "bulk",
        "recommendations_batch",
        job_id=f"recs:{event.student_id}",
        defer_by=_URGENT_DEBOUNCE_S,
        student_id=str(event.student_id),
        urgent=True,
    )
    return updated


async def log_decline(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> RecommendationOut | None:
    """A decline changes nothing but the row — and the student's feed."""
    if event.type != EventType.recommendation_declined:
        return None
    payload = RecommendationDeclinedPayload.model_validate(event.payload)
    row = await recs_repo.get(session, event.student_id, payload.recommendation_id)
    if row is None:
        return None
    if row.status == "declined":
        return row
    if row.status in ("accepted", "expired"):
        raise Conflict("recommendation already decided")
    _logger.info(
        "recommendation_declined",
        student_id=str(event.student_id),
        kind=row.kind,
        reason_hash=row.reason_hash,
    )
    return await recs_repo.decide(
        session,
        event.student_id,
        row.id,
        "declined",
        now=deps.now(),
        decision_event_id=event.id,
    )


async def _still_actionable(
    session: AsyncSession, student_id: UUID, action: RecommendationAction
) -> bool:
    if action.kind == "program_remove" and action.program_id:
        saved = await programs_repo.list_saved(session, student_id)
        return any(item.program_id == action.program_id for item in saved)
    if action.kind in ("set_open", "set_edit") and action.set_id:
        target = await sets_repo.get_set(session, student_id, action.set_id)
        return target is not None and target.status != "done"
    return True


async def _perform(
    session: AsyncSession,
    event: Event,
    deps: RuleDeps,
    action: RecommendationAction,
) -> None:
    """Write the nested event; the phase-2 rules do the rest."""
    if action.kind == "profile_update" and action.profile_path is not None:
        await _profile_update(
            session, event, deps, action.profile_path, action.profile_value
        )
        return
    if action.kind == "requirement_update" and action.exam_id is not None:
        if action.test_date is not None:
            path = (
                "academics.sat_date"
                if action.exam_id == "SAT_MATH"
                else "academics.ent_date"
            )
            await _profile_update(
                session, event, deps, path, action.test_date.isoformat()
            )
        if action.target_score is not None:
            path = (
                "academics.sat_target"
                if action.exam_id == "SAT_MATH"
                else "academics.ent_target"
            )
            await _profile_update(session, event, deps, path, int(action.target_score))
        return
    if action.kind == "program_remove" and action.program_id:
        await programs_repo.remove_saved(session, event.student_id, action.program_id)
        await events_store.append(
            session,
            deps.redis,
            EventIn(
                type=EventType.program_removed,
                payload=ProgramSavedPayload(program_id=action.program_id).model_dump(
                    mode="json"
                ),
                student_id=event.student_id,
            ),
            deps,
        )
        return
    if action.kind == "set_open" and action.set_id is not None:
        target = await apply_sets.open_set(
            session, deps, event.student_id, action.set_id
        )
        await events_store.append(
            session,
            deps.redis,
            EventIn(
                type=EventType.set_opened,
                payload=SetOpenedPayload(
                    set_id=action.set_id,
                    skill_ids=[topic.skill_id for topic in target.topics],
                ).model_dump(mode="json"),
                student_id=event.student_id,
                exam_id=target.exam_id,
                set_id=action.set_id,
            ),
            deps,
        )
        return
    if action.kind == "set_edit" and action.set_id is not None:
        target = await sets_repo.get_set(session, event.student_id, action.set_id)
        if target is None:
            return
        await sets_repo.update_set(
            session,
            event.student_id,
            action.set_id,
            action.skill_ids,
            action.deadline,
        )
        if action.deadline is not None and action.deadline != target.deadline:
            await events_store.append(
                session,
                deps.redis,
                EventIn(
                    type=EventType.set_deadline_changed,
                    payload=SetDeadlineChangedPayload(
                        set_id=action.set_id,
                        old=target.deadline,
                        new=action.deadline,
                    ).model_dump(mode="json"),
                    student_id=event.student_id,
                    exam_id=target.exam_id,
                    set_id=action.set_id,
                ),
                deps,
            )
        return
    # `milestone_open` и `acknowledge` ничего не меняют — это навигация.


async def _profile_update(
    session: AsyncSession,
    event: Event,
    deps: RuleDeps,
    path: str,
    value: Any,
) -> None:
    await profiles_repo.apply_profile_update(
        session,
        event.student_id,
        ProfileUpdateIn(path=path, value=value, by="user"),
    )
    await events_store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.profile_updated,
            payload=ProfileUpdatedPayload(
                field=path, value=value, by="user"
            ).model_dump(mode="json"),
            student_id=event.student_id,
        ),
        deps,
    )


# --- handlers that only enqueue (§2.2) ---


async def on_profile_updated_enqueue(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """A profile edit can change the soft match, the search warm-up and the
    urgency of the feed — all three are jobs, none of them is a rule."""
    if event.type != EventType.profile_updated:
        return
    field = str((event.payload or {}).get("field") or "")
    profile = await profiles_repo.get_profile(session, event.student_id)

    if any(field.startswith(prefix) for prefix in _SOFT_MATCH_PREFIXES):
        summary = (profile.traits.summary or "").strip()
        if summary:
            from app.apply.soft import summary_hash

            deps.jobs.enqueue(
                "bulk",
                "soft_match",
                job_id=f"softmatch:{event.student_id}:{summary_hash(summary)[:12]}",
                defer_by=deps.params.soft_match_debounce_s,
                student_id=str(event.student_id),
                program_ids=[],
            )

    if field.startswith(("direction.", "preferences.countries")):
        await _warm_search(deps, event.student_id, profile)

    if field in _URGENT_PROFILE_FIELDS:
        enqueue_urgent(deps, event.student_id)


async def _warm_search(deps: RuleDeps, student_id: UUID, profile: Any) -> None:
    """Pre-fill the catalogue for the student's direction, at most hourly."""
    if profile.readiness < deps.params.assistant_readiness_threshold:
        return
    direction = profile.questionnaire.direction.field.value
    if not direction:
        return
    countries = (profile.questionnaire.preferences.countries.value or [])[:3]
    hour = deps.now().strftime("%Y%m%d%H")
    for index, country in enumerate(countries or [""]):
        query = f"{direction} bachelor program admission requirements {country}".strip()
        deps.jobs.enqueue(
            "bulk",
            "search_programs",
            job_id=f"warm:{student_id}:{hour}:{index}",
            query=query,
            student_id=str(student_id),
            warm=True,
        )


def enqueue_urgent(deps: RuleDeps, student_id: UUID) -> None:
    deps.jobs.enqueue(
        "bulk",
        "recommendations_batch",
        job_id=f"recs:{student_id}",
        defer_by=_URGENT_DEBOUNCE_S,
        student_id=str(student_id),
        urgent=True,
    )


async def enqueue_recs_urgent(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """Every event of §0.2 that can make the plan wrong right now."""
    del session
    enqueue_urgent(deps, event.student_id)


def now_utc() -> datetime:
    return datetime.now(UTC)
