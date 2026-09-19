"""B1 rules for the observer's events — memory-architecture §8.1, §5.4.

Source: docs/tz/phase3-agents.md §3.10, §3.11 (rule half), §5.2 F5–F7, F9.

`observation.extracted` carries the observer's output whole; this rule
decides what of it becomes knowledge: `Evidence`, the next `KnowledgeState`,
misconception statuses, `ROOT_CAUSE` edges, a `task.answered` for a task
answered in the chat, pace signals. The model never writes here — only this
code, inside `dispatch`, in the job's Postgres transaction.

Idempotent per event: evidence by `(event_id, skill_id, ordinal)` (read up
front and MERGE-keyed), a chat answer by `task_instances.answered_at`, roots
by MERGE, pace signals by `(event_id, ordinal)`; a repeated dispatch applies
nothing and does not bump the knowledge version.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app import keys
from app.apply._lock import student_lock
from app.db.repo import aggregates as aggregates_repo
from app.db.repo import messages as messages_repo
from app.db.repo import sets as sets_repo
from app.db.repo import tasks as tasks_repo
from app.events import store
from app.events.dispatch import GraphUnavailable, RuleDeps
from app.events.session import session_minute
from app.events.version import bump
from app.events.version import get as version_get
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge import weights
from app.knowledge.misconceptions import merge_triggers
from app.knowledge.reconcile import reconcile_chat_evidence
from app.schemas.common import ExamId
from app.schemas.events import (
    Event,
    EventIn,
    EventType,
    MisconceptionCanonizedPayload,
    MisconceptionPersonalCreatedPayload,
    ObservationExtractedPayload,
    TaskAnsweredPayload,
)
from app.schemas.knowledge import (
    EvidenceContext,
    EvidenceIn,
    KnowledgeStateOut,
    MisconceptionStateOut,
)
from app.schemas.observer import Observation, ObservationApplyResult
from app.schemas.tasks import TaskInstance

_logger = structlog.get_logger(__name__)

_EVIDENCE_KINDS = {"solution_step", "applied", "confusion", "question", "avoided_trap"}
_POSITIVE_KINDS = {"applied", "avoided_trap"}
_NEGATIVE_KINDS = {"confusion", "question"}
_EXAMS: tuple[ExamId, ...] = ("SAT_MATH", "ENT_MATH")
_ROOT_HINT_CONFIDENCE = 0.6
_MAX_CHAT_ANSWER_SEC = 3600
_WINDOW_TYPES = [
    EventType.message_user,
    EventType.message_assistant,
    EventType.task_issued,
]


# --- observation.extracted ---


async def apply_observation_extracted(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> ObservationApplyResult | object:
    payload = ObservationExtractedPayload.model_validate(event.payload)
    if deps.graph is None:
        _logger.warning("observation_graph_unavailable", event_id=event.id)
        return GraphUnavailable

    try:
        slice_ = await _Slice.load(session, deps, event, payload)
        applied_keys = await personal_q.list_evidence_keys_for_event(
            deps.graph, event.student_id, event.id
        )
    except (ServiceUnavailable, SessionExpired):
        _logger.warning("observation_graph_unavailable", event_id=event.id)
        return GraphUnavailable

    result = ObservationApplyResult(event_id=event.id)
    written_incorrect: dict[str, str] = {}
    async with student_lock(deps.redis, event.student_id):
        for ordinal, obs in enumerate(payload.observations):
            reason = _filter(obs, ordinal, slice_, applied_keys, deps)
            if reason is not None:
                _skip(result, event, ordinal, obs, reason)
                continue
            try:
                reason = await _apply_one(
                    session,
                    deps,
                    event,
                    payload,
                    slice_,
                    ordinal,
                    obs,
                    result,
                    written_incorrect,
                )
            except (ServiceUnavailable, SessionExpired):
                _logger.warning(
                    "observation_graph_unavailable",
                    event_id=event.id,
                    ordinal=ordinal,
                    applied=result.applied,
                )
                return GraphUnavailable
            if reason is not None:
                _skip(result, event, ordinal, obs, reason)
            elif obs.skill_id is not None and obs.kind in _EVIDENCE_KINDS:
                applied_keys.add((obs.skill_id, ordinal))

    if result.applied > 0 or result.task_answered_event_ids:
        await _after_change(session, deps, event.student_id, slice_)
        result.knowledge_version = await bump(deps.redis, event.student_id)
    else:
        result.knowledge_version = await version_get(deps.redis, event.student_id)

    _logger.info(
        "observation_applied",
        event_id=event.id,
        applied=result.applied,
        skipped=len(result.skipped),
        task_answered=len(result.task_answered_event_ids),
        canon=len(result.pending_canonizations),
        version=result.knowledge_version,
    )
    return result


class _Slice:
    """Everything the rule checks an observation against."""

    def __init__(self) -> None:
        self.exam_id: ExamId = "SAT_MATH"
        self.set_id: UUID | None = None
        self.topic_skill_id: str | None = None
        self.skill_ids: set[str] = set()
        self.misconception_ids: set[str] = set()
        self.source_event_ids: set[int] = set()
        self.window: dict[int, Event] = {}
        self.chat_id: UUID | None = None

    @classmethod
    async def load(
        cls,
        session: AsyncSession,
        deps: RuleDeps,
        event: Event,
        payload: ObservationExtractedPayload,
    ) -> _Slice:
        slice_ = cls()
        slice_.exam_id = payload.exam_id
        slice_.set_id = payload.set_id
        slice_.topic_skill_id = payload.topic_skill_id
        slice_.chat_id = event.chat_id
        slice_.source_event_ids = set(event.source_event_ids or [])

        roots: list[str] = []
        if payload.topic_skill_id is not None:
            roots = [payload.topic_skill_id]
        else:
            set_out = await sets_repo.get_set(session, event.student_id, payload.set_id)
            roots = [t.skill_id for t in set_out.topics] if set_out else []
        skill_ids = set(roots)
        for root in roots:
            for prerequisite in await canonical_q.get_prerequisites(
                deps.graph, root, depth=2
            ):
                skill_ids.add(prerequisite.skill_id)
        slice_.skill_ids = skill_ids

        known: set[str] = set()
        for skill_id in sorted(skill_ids):
            for ref in await canonical_q.list_misconceptions_for_skill(
                deps.graph, skill_id
            ):
                known.add(ref.id)
        for state in await personal_q.get_misc_states(
            deps.graph, event.student_id, sorted(skill_ids)
        ):
            known.add(state.misconception_id)
        slice_.misconception_ids = known

        for window_event in await store.get_events(
            session, event.student_id, sorted(slice_.source_event_ids)
        ):
            slice_.window[window_event.id] = window_event
        return slice_

    def occurred_at(
        self, event_ids: list[int], *, last: bool = True
    ) -> datetime | None:
        known = [self.window[i] for i in event_ids if i in self.window]
        if not known:
            return None
        chosen = (
            max(known, key=lambda e: e.id) if last else min(known, key=lambda e: e.id)
        )
        return chosen.occurred_at


def _filter(
    obs: Observation,
    ordinal: int,
    slice_: _Slice,
    applied_keys: set[tuple[str, int]],
    deps: RuleDeps,
) -> str | None:
    if (
        obs.kind != "pace_signal"
        and (obs.confidence or 0.0) < deps.params.observer_min_confidence
    ):
        return "low_confidence"
    if obs.skill_id is not None and obs.skill_id not in slice_.skill_ids:
        return "unknown_skill"
    if (
        obs.misconception_id is not None
        and obs.kind != "proposed_misconception"
        and obs.misconception_id not in slice_.misconception_ids
    ):
        return "unknown_misconception"
    if obs.root_skill_id is not None and obs.root_skill_id not in slice_.skill_ids:
        return "unknown_root"
    if not set(obs.event_ids) <= slice_.source_event_ids:
        return "event_ids_outside_window"
    if obs.skill_id is not None and (obs.skill_id, ordinal) in applied_keys:
        return "already_applied"
    return None


def _skip(
    result: ObservationApplyResult,
    event: Event,
    ordinal: int,
    obs: Observation,
    reason: str,
) -> None:
    result.skipped.append((ordinal, reason))
    _logger.info(
        "observation_skipped",
        event_id=event.id,
        ordinal=ordinal,
        kind=obs.kind,
        reason=reason,
    )


async def _apply_one(
    session: AsyncSession,
    deps: RuleDeps,
    event: Event,
    payload: ObservationExtractedPayload,
    slice_: _Slice,
    ordinal: int,
    obs: Observation,
    result: ObservationApplyResult,
    written_incorrect: dict[str, str],
) -> str | None:
    """Apply one observation; a string is the reason it was skipped."""
    if obs.kind in _EVIDENCE_KINDS:
        return await _apply_evidence(
            session, deps, event, slice_, ordinal, obs, result, written_incorrect
        )
    if obs.kind == "task_in_chat":
        return await _apply_task_in_chat(session, deps, event, slice_, obs, result)
    if obs.kind == "root_hint":
        assert obs.skill_id is not None and obs.root_skill_id is not None
        evidence_id = written_incorrect.get(obs.skill_id)
        if evidence_id is None:
            latest = await personal_q.latest_incorrect_evidence(
                deps.graph, event.student_id, obs.skill_id
            )
            if latest is None:
                return "no_incorrect_evidence"
            evidence_id = latest.evidence_id
        created = await personal_q.add_root_cause(
            deps.graph,
            evidence_id,
            obs.root_skill_id,
            _ROOT_HINT_CONFIDENCE,
            "observer",
        )
        if not created:
            return "already_applied"
        result.applied += 1
        return None
    if obs.kind == "proposed_misconception":
        if obs.skill_id is None and slice_.topic_skill_id is None:
            return "no_skill"
        # Постановку канонизации делает job: apply/ не знает про очередь.
        result.pending_canonizations.append(ordinal)
        return None
    if obs.kind == "pace_signal":
        day = (slice_.occurred_at(obs.event_ids) or event.occurred_at).date()
        await aggregates_repo.add_pace_signal(
            session, event.student_id, day, obs.signal or "", event.id, ordinal
        )
        return None
    return "unknown_kind"


async def _context_for(
    session: AsyncSession,
    event: Event,
    slice_: _Slice,
    event_ids: list[int],
) -> tuple[EvidenceContext, datetime]:
    """Evidence context of the message an observation is based on."""
    known = sorted(i for i in event_ids if i in slice_.window)
    first = slice_.window[known[0]] if known else None
    observed_at = slice_.occurred_at(event_ids) or event.occurred_at
    source_session = first.session_id if first is not None else event.session_id
    minute = (
        await session_minute(session, event.student_id, source_session, observed_at)
        if source_session is not None
        else None
    )
    message_ids = await messages_repo.list_by_event_ids(
        session, event.student_id, known
    )
    message_id = next((message_ids[i] for i in known if i in message_ids), None)
    hint_level = await _hint_level_before(session, event, slice_, known)
    return (
        EvidenceContext(
            mode="chat",
            session_minute=minute,
            topic_skill_id=slice_.topic_skill_id,
            session_id=source_session,
            hint_level_before=hint_level,
            message_id=message_id,
        ),
        observed_at,
    )


async def _hint_level_before(
    session: AsyncSession, event: Event, slice_: _Slice, known: list[int]
) -> int | None:
    """`markup.hint_level` of the last tutor message before the source one."""
    if not known:
        return None
    before = known[0]
    in_window = [
        e
        for i, e in slice_.window.items()
        if i < before and e.type == EventType.message_assistant
    ]
    previous = max(in_window, key=lambda e: e.id) if in_window else None
    if previous is None and slice_.chat_id is not None:
        previous = await store.latest_before(
            session,
            event.student_id,
            slice_.chat_id,
            [EventType.message_assistant],
            before,
        )
    if previous is None:
        return None
    value = (previous.payload or {}).get("hint_level")
    return int(value) if isinstance(value, int) else None


async def _states(
    deps: RuleDeps, student_id: UUID, skill_id: str, exam_id: ExamId
) -> tuple[KnowledgeStateOut | None, KnowledgeStateOut | None]:
    state = await personal_q.get_state(deps.graph, student_id, skill_id, exam_id)
    cross = None
    if skill_id.startswith("math."):
        other = next((e for e in _EXAMS if e != exam_id), None)
        if other is not None:
            cross = await personal_q.get_state(deps.graph, student_id, skill_id, other)
    return state, cross


def _existing_triggers(
    misc_states: list[MisconceptionStateOut], misconception_id: str
) -> dict[str, Any]:
    for state in misc_states:
        if state.misconception_id == misconception_id:
            return dict(state.triggers or {})
    return {}


async def _apply_evidence(
    session: AsyncSession,
    deps: RuleDeps,
    event: Event,
    slice_: _Slice,
    ordinal: int,
    obs: Observation,
    result: ObservationApplyResult,
    written_incorrect: dict[str, str],
) -> str | None:
    assert obs.skill_id is not None
    kind = obs.kind
    if kind == "solution_step":
        direction = 1 if obs.outcome == "correct" else -1
    elif kind in _POSITIVE_KINDS:
        direction = 1
    else:
        direction = -1

    misc_states = await personal_q.get_misc_states(
        deps.graph, event.student_id, [obs.skill_id]
    )
    avoided = kind == "avoided_trap"
    misconception_id = None
    if avoided or (kind == "solution_step" and direction == -1):
        misconception_id = obs.misconception_id
    if avoided and not any(m.misconception_id == misconception_id for m in misc_states):
        return "no_misconception_state"

    context, observed_at = await _context_for(session, event, slice_, obs.event_ids)
    tier = weights.tier_for("chat", "chat", kind)
    evidence = EvidenceIn(
        event_id=event.id,
        ordinal=ordinal,
        skill_id=obs.skill_id,
        exam_id=slice_.exam_id,
        kind=kind,
        tier=tier,
        source="chat",
        weight=weights.evidence_weight(
            "chat", "chat", kind, seen_before=False, matched=True, params=deps.params
        ),
        direction=direction,  # type: ignore[arg-type]
        summary=obs.summary,
        context=context,
        observed_at=observed_at,
        extractor_version=event.extractor_version,
    )
    state, cross = await _states(deps, event.student_id, obs.skill_id, slice_.exam_id)
    reconciled = reconcile_chat_evidence(
        evidence,
        state,
        misc_states,
        misconception_id,
        avoided,
        deps.params,
        deps.now(),
        cross_state=cross,
    )
    change = reconciled.misconception_change
    triggers = None
    if change is not None:
        triggers = _existing_triggers(misc_states, change.misconception_id)
        if not avoided:
            triggers = merge_triggers(triggers, evidence, params=deps.params)
    evidence_id = await personal_q.apply_chat_observation_tx(
        deps.graph,
        event.student_id,
        evidence,
        reconciled.state_after,
        change,
        triggers,
        event.id,
        cross_state=reconciled.cross_exam_state,
    )
    if direction == -1:
        written_incorrect[obs.skill_id] = evidence_id
    if obs.skill_id not in result.skills_changed:
        result.skills_changed.append(obs.skill_id)
    if change is not None:
        result.misconceptions_changed.append(change)
    result.applied += 1
    return None


_LETTER_RE = re.compile(r"\b([A-Ea-eАВСДЕавсде])\b")
_NUMBER_RE = re.compile(r"[-−–]?\d+(?:[.,]\d+)?(?:/\d+)?")
_CYRILLIC_LETTERS = str.maketrans("АВСДЕавсде", "ABCDEabcde")


def normalize_chat_answer(instance: TaskInstance, raw: str) -> Any | None:
    """The observer's `answer` in the instance's own format, or None.

    mcq — one option letter (case and Cyrillic look-alikes ignored);
    multi_select — a list of letters; numeric — the number as a string.
    """
    text = (raw or "").strip()
    if not text:
        return None
    keys_ = {option.key.upper() for option in instance.options}
    if instance.type in ("mcq4", "mcq5"):
        letters = [
            m.group(1).translate(_CYRILLIC_LETTERS).upper()
            for m in _LETTER_RE.finditer(text)
        ]
        letters = [letter for letter in letters if not keys_ or letter in keys_]
        return letters[-1] if letters else None
    if instance.type == "multi_select":
        compact = text.translate(_CYRILLIC_LETTERS).upper()
        letters = [ch for ch in compact if ch in (keys_ or set("ABCDE"))]
        seen: list[str] = []
        for letter in letters:
            if letter not in seen:
                seen.append(letter)
        return seen or None
    match = _NUMBER_RE.search(text.replace("−", "-").replace("–", "-"))
    if match is None:
        return None
    return match.group(0).replace(",", ".")


async def _apply_task_in_chat(
    session: AsyncSession,
    deps: RuleDeps,
    event: Event,
    slice_: _Slice,
    obs: Observation,
    result: ObservationApplyResult,
) -> str | None:
    try:
        instance_id = UUID(str(obs.instance_id))
    except ValueError:
        return "unknown_instance"
    instance = await tasks_repo.get_instance(session, event.student_id, instance_id)
    if instance is None:
        return "unknown_instance"
    issued_ids = await tasks_repo.issued_event_ids(
        session, event.student_id, [instance_id]
    )
    issued_id = issued_ids.get(instance_id)
    issued = (
        slice_.window.get(issued_id)
        if issued_id is not None and issued_id in slice_.window
        else (
            await store.get_event(session, event.student_id, issued_id)
            if issued_id is not None
            else None
        )
    )
    if issued is None or issued.chat_id != event.chat_id:
        return "unknown_instance"
    if await tasks_repo.get_answered_at(session, instance_id) is not None:
        return "already_answered"

    answer = normalize_chat_answer(instance, obs.answer or "")
    if answer is None:
        return "unparsable_answer"

    context, answered_at = await _context_for(session, event, slice_, obs.event_ids)
    spent = int((answered_at - issued.occurred_at).total_seconds())
    known = sorted(i for i in obs.event_ids if i in slice_.window)
    answer_event = slice_.window[known[-1]] if known else None
    answered = await store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.task_answered,
            payload=TaskAnsweredPayload(
                instance_id=instance_id,
                answer=answer,
                time_spent_sec=max(0, min(_MAX_CHAT_ANSWER_SEC, spent)),
                mode="chat",
                session_minute=context.session_minute or 0,
                after_guideline=False,
                hint_level_before=context.hint_level_before or 0,
            ).model_dump(mode="json"),
            student_id=event.student_id,
            session_id=answer_event.session_id if answer_event else event.session_id,
            exam_id=instance.exam_id,
            set_id=slice_.set_id,
            topic_skill_id=slice_.topic_skill_id,
            chat_id=event.chat_id,
            occurred_at=answered_at,
            source_event_ids=[event.id],
        ),
        deps,
        dispatch_event=True,
    )
    result.task_answered_event_ids.append(answered.id)
    return None


async def _after_change(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, slice_: _Slice
) -> None:
    """Sets follow the knowledge model; the cached context is stale now."""
    from app.apply.sets import rebuild_sets

    await rebuild_sets(session, deps, student_id, slice_.exam_id)
    await _drop_context(deps, student_id, slice_.topic_skill_id, slice_.set_id)


async def _drop_context(
    deps: RuleDeps, student_id: UUID, topic_skill_id: str | None, set_id: UUID | None
) -> None:
    names = []
    if topic_skill_id is not None:
        names.append(keys.ctx_topic(str(student_id), topic_skill_id))
    if set_id is not None:
        names.append(keys.ctx_topic(str(student_id), f"set:{set_id}"))
    if not names:
        return
    try:
        await deps.redis.delete(*names)
    except Exception:  # noqa: BLE001 — the version bump invalidates it anyway
        _logger.warning("ctx_topic_invalidate_failed", student_id=str(student_id))


# --- canonization results (§5.4, phase3 §3.11) ---


async def apply_misconception_personal_created(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> ObservationApplyResult | object:
    """Create the personal `Misconception` node, then count it as a hit."""
    payload = MisconceptionPersonalCreatedPayload.model_validate(event.payload)
    if deps.graph is None:
        return GraphUnavailable
    try:
        await canonical_q.create_personal_misconception(
            deps.graph,
            event.student_id,
            payload.misconception_id,
            payload.name,
            payload.description,
            payload.error_class,
            payload.skill_id,
            payload.embedding,
            payload.source_event_id,
            payload.ordinal,
        )
    except (ServiceUnavailable, SessionExpired):
        return GraphUnavailable
    return await _misconception_hit(
        session,
        deps,
        event,
        misconception_id=payload.misconception_id,
        skill_id=payload.skill_id,
        description=payload.description,
        source_event_id=payload.source_event_id,
        ordinal=payload.ordinal,
    )


async def apply_misconception_canonized(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> ObservationApplyResult | object:
    """A proposed misconception turned out to be a known one: count a hit."""
    payload = MisconceptionCanonizedPayload.model_validate(event.payload)
    if deps.graph is None:
        return GraphUnavailable
    return await _misconception_hit(
        session,
        deps,
        event,
        misconception_id=payload.canonical_id,
        skill_id=payload.skill_id,
        description=payload.description,
        source_event_id=payload.source_event_id,
        ordinal=payload.ordinal,
    )


async def _misconception_hit(
    session: AsyncSession,
    deps: RuleDeps,
    event: Event,
    *,
    misconception_id: str,
    skill_id: str,
    description: str,
    source_event_id: int,
    ordinal: int,
) -> ObservationApplyResult | object:
    result = ObservationApplyResult(event_id=event.id)
    source = await store.get_event(session, event.student_id, source_event_id)
    source_payload = (
        ObservationExtractedPayload.model_validate(source.payload)
        if source is not None and source.type == EventType.observation_extracted
        else None
    )
    exam_id: ExamId = (
        source_payload.exam_id if source_payload else (event.exam_id or "SAT_MATH")
    )
    topic_skill_id = source_payload.topic_skill_id if source_payload else None
    set_id = source_payload.set_id if source_payload else event.set_id
    observed_at = source.occurred_at if source is not None else event.occurred_at

    message_id = None
    if source_payload is not None and 0 <= ordinal < len(source_payload.observations):
        event_ids = sorted(source_payload.observations[ordinal].event_ids)
        ids = await messages_repo.list_by_event_ids(
            session, event.student_id, event_ids
        )
        message_id = next((ids[i] for i in event_ids if i in ids), None)

    try:
        async with student_lock(deps.redis, event.student_id):
            keys_done = await personal_q.list_evidence_keys_for_event(
                deps.graph, event.student_id, event.id
            )
            if (skill_id, 0) in keys_done:
                result.skipped.append((0, "already_applied"))
                result.knowledge_version = await version_get(
                    deps.redis, event.student_id
                )
                return result
            evidence = EvidenceIn(
                event_id=event.id,
                ordinal=0,
                skill_id=skill_id,
                exam_id=exam_id,
                kind="misconception_hit",
                tier=2,
                source="chat",
                weight=weights.base_weight("chat", "chat", "solution_step"),
                direction=-1,
                summary=description[:300],
                context=EvidenceContext(
                    mode="chat",
                    topic_skill_id=topic_skill_id,
                    message_id=message_id,
                ),
                observed_at=observed_at,
                extractor_version=source.extractor_version if source else None,
            )
            misc_states = await personal_q.get_misc_states(
                deps.graph, event.student_id, [skill_id]
            )
            state, cross = await _states(deps, event.student_id, skill_id, exam_id)
            reconciled = reconcile_chat_evidence(
                evidence,
                state,
                misc_states,
                misconception_id,
                False,
                deps.params,
                deps.now(),
                cross_state=cross,
            )
            change = reconciled.misconception_change
            triggers = merge_triggers(
                _existing_triggers(misc_states, misconception_id),
                evidence,
                params=deps.params,
            )
            await personal_q.apply_chat_observation_tx(
                deps.graph,
                event.student_id,
                evidence,
                reconciled.state_after,
                change,
                triggers,
                event.id,
                cross_state=reconciled.cross_exam_state,
            )
    except (ServiceUnavailable, SessionExpired):
        return GraphUnavailable

    result.applied = 1
    result.skills_changed = [skill_id]
    if change is not None:
        result.misconceptions_changed = [change]
    await _drop_context(deps, event.student_id, topic_skill_id, set_id)
    result.knowledge_version = await bump(deps.redis, event.student_id)
    _logger.info(
        "observation_applied",
        event_id=event.id,
        applied=1,
        skipped=0,
        task_answered=0,
        canon=0,
        version=result.knowledge_version,
    )
    return result
