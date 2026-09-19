"""Context assembler for the tutor agent — the `<learner_model>` slots.

Source: memory-architecture-quack.md §9.2–§9.3; docs/tz/phase3-agents.md
§3.7, §5.1 C7, §5.2 F4.

Four graph reads (`graph.queries.context` Q1–Q4) run in parallel; their raw
rows are cached in Redis under `keys.ctx_topic` and are valid while the
student's `knowledge_version` and the set stay the same. Slots that depend on
Postgres (`deadline`, `profile`, `previous_set`, the "в сете i из n" part of
`topic`) come in through `ContextExtras` and are rebuilt on every call —
`apply.context.get_topic_context` gathers them, so this module never touches
the database layer.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

import structlog
from neo4j import AsyncDriver
from pydantic import BaseModel
from redis.asyncio import Redis

from app import keys
from app.config import KnowledgeParams, settings
from app.events import version as knowledge_version
from app.graph.queries import canonical as canonical_q
from app.graph.queries import context as context_q
from app.knowledge import words
from app.knowledge.hlr import due_at, recall_p
from app.knowledge.misconceptions import trigger_words, visible_to
from app.schemas.common import ExamId
from app.schemas.knowledge import KnowledgeStateOut, MisconceptionStateOut, TestDate
from app.schemas.profile import Profile
from app.schemas.sets import SetOut

_logger = structlog.get_logger(__name__)

SLOT_ORDER: tuple[str, ...] = (
    "topic",
    "strengths",
    "prerequisite_gaps",
    "active_misconceptions",
    "under_watch",
    "low_data",
    "deadline",
    "profile",
    "previous_set",
)
_LIMITS: dict[str, int] = {
    "topic": 1,
    "strengths": 2,
    "prerequisite_gaps": 3,
    "active_misconceptions": 2,
    "under_watch": 1,
    "low_data": 2,
    "deadline": 2,
    "profile": 3,
    "previous_set": 1,
}
# Over budget, slots are cut from the bottom of the table first (§3.7).
_TRUNCATE_ORDER: tuple[str, ...] = (
    "previous_set",
    "low_data",
    "under_watch",
    "profile",
    "deadline",
    "prerequisite_gaps",
    "strengths",
    "active_misconceptions",
    "topic",
)
_MONTHS = (
    "янв",
    "фев",
    "мар",
    "апр",
    "мая",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
)
_EXAM_LABEL: dict[str, str] = {"SAT_MATH": "SAT", "ENT_MATH": "ЕНТ"}
_HINT_LEVEL: dict[str, int] = {"minimal": 1, "normal": 2, "generous": 3}
_PREVIOUS_SET_CHARS = 300
_DUE_SOON_DAYS = 7


class TopicContext(BaseModel):
    """Slots for the tutor's context block (memory-architecture §9.2).

    Each slot is a list of short strings, already formatted for injection.
    Order in the injected block: topic, strengths, prerequisite_gaps,
    active_misconceptions, under_watch, low_data, deadline, profile, previous_set.

    Service fields (phase 3, C7) are not slots: `skill_ids` is the topic skill
    and its prerequisites (what `get_task` may be asked for), `topic_name`,
    `set_label`, `as_of` go into the block header, `cache` tells whether the
    graph part came from Redis.
    """

    topic: list[str] = []
    strengths: list[str] = []
    prerequisite_gaps: list[str] = []
    active_misconceptions: list[str] = []
    under_watch: list[str] = []
    low_data: list[str] = []
    deadline: list[str] = []
    profile: list[str] = []
    previous_set: list[str] = []

    skill_ids: list[str] = []
    topic_name: str = ""
    set_label: str = ""
    as_of: datetime | None = None
    cache: Literal["hit", "miss", "none"] = "none"


class ContextExtras(BaseModel):
    """What the Postgres side contributes to the context (`apply.context`)."""

    set: SetOut | None = None
    profile: Profile
    previous_summary: str | None = None
    p_target: float


class GraphRaw(BaseModel):
    """Raw results of the four queries — the cached part."""

    skill_ids: list[str]
    q1: list[context_q.SkillSliceRow]
    q2: dict[str, tuple[int, float]]
    q3: list[MisconceptionStateOut]
    q4: list[TestDate]


async def build_topic_context(
    driver: AsyncDriver,
    redis: Redis | None,
    student_id: UUID,
    topic_skill_id: str | None,
    set_id: UUID,
    *,
    exam_id: ExamId,
    extras: ContextExtras,
    params: KnowledgeParams,
    now: datetime,
) -> TopicContext:
    """Assemble the tutor context; `topic_skill_id=None` is the set's chat."""
    started = time.perf_counter()
    cache_key = keys.ctx_topic(str(student_id), topic_skill_id or f"set:{set_id}")

    raw, cache = await _cached(redis, cache_key, student_id, set_id, exam_id)
    if raw is None:
        raw = await _query(
            driver, student_id, topic_skill_id, extras.set, exam_id, params, now
        )
        if cache != "none":
            await _store(redis, cache_key, student_id, set_id, exam_id, raw, now)

    context = _assemble(raw, topic_skill_id, extras, params, now)
    truncated = _truncate(context, params.context_budget_tokens * 3)
    context.cache = cache
    _logger.info(
        "ctx_topic",
        student_id=str(student_id),
        skill=topic_skill_id,
        set_id=str(set_id),
        cache=cache,
        ms=round((time.perf_counter() - started) * 1000, 1),
        truncated=truncated,
        slots={name: len(getattr(context, name)) for name in SLOT_ORDER},
    )
    return context


# --- cache ---


async def _cached(
    redis: Redis | None,
    key: str,
    student_id: UUID,
    set_id: UUID,
    exam_id: str,
) -> tuple[GraphRaw | None, Literal["hit", "miss", "none"]]:
    if redis is None:
        return None, "none"
    try:
        current = await knowledge_version.get(redis, student_id)
        value = await redis.get(key)
    except Exception:  # noqa: BLE001 — Redis down: build without the cache
        _logger.warning("ctx_topic_cache_unavailable", student_id=str(student_id))
        return None, "none"
    if value is None:
        return None, "miss"
    try:
        payload = json.loads(value)
        if (
            payload.get("version") != current
            or payload.get("set_id") != str(set_id)
            or payload.get("exam_id") != exam_id
        ):
            return None, "miss"
        return GraphRaw.model_validate(payload["graph"]), "hit"
    except (ValueError, TypeError, KeyError, AttributeError):
        # Повреждённый ключ — как промах; при записи он будет перезаписан.
        _logger.warning("ctx_topic_cache_corrupted", key=key)
        return None, "miss"


async def _store(
    redis: Redis | None,
    key: str,
    student_id: UUID,
    set_id: UUID,
    exam_id: str,
    raw: GraphRaw,
    now: datetime,
) -> None:
    if redis is None:
        return
    try:
        current = await knowledge_version.get(redis, student_id)
        await redis.set(
            key,
            json.dumps(
                {
                    "version": current,
                    "set_id": str(set_id),
                    "exam_id": exam_id,
                    "built_at": now.isoformat(),
                    "graph": raw.model_dump(mode="json"),
                },
                ensure_ascii=False,
            ),
            ex=settings.CTX_CACHE_TTL_S,
        )
    except Exception:  # noqa: BLE001
        _logger.warning("ctx_topic_cache_write_failed", key=key)


# --- the four queries ---


async def _query(
    driver: AsyncDriver,
    student_id: UUID,
    topic_skill_id: str | None,
    set_out: SetOut | None,
    exam_id: str,
    params: KnowledgeParams,
    now: datetime,
) -> GraphRaw:
    roots = (
        [topic_skill_id]
        if topic_skill_id is not None
        else [topic.skill_id for topic in (set_out.topics if set_out else [])]
    )
    skill_ids: list[str] = list(roots)
    for root in roots:
        for prerequisite in await canonical_q.get_prerequisites(driver, root, depth=2):
            if prerequisite.skill_id not in skill_ids:
                skill_ids.append(prerequisite.skill_id)

    q1, q2, q3, q4 = await asyncio.gather(
        context_q.q_skill_slice(driver, student_id, exam_id, skill_ids),
        context_q.q_root_causes(driver, student_id, skill_ids, params.root_window_days),
        context_q.q_misconceptions(driver, student_id, skill_ids),
        context_q.q_test_dates(driver, exam_id, now.date()),
    )
    return GraphRaw(skill_ids=skill_ids, q1=q1, q2=q2, q3=q3, q4=q4)


# --- slots ---


def _fresh(state: KnowledgeStateOut | None, now: datetime) -> KnowledgeStateOut | None:
    """Recall at `now` — cached rows carry the recall of their build time."""
    if state is None:
        return None
    return state.model_copy(
        update={"p_recall": recall_p(state.half_life_h, state.last_observed_at, now)}
    )


def _pc(state: KnowledgeStateOut) -> str:
    return f"p={state.p_recall:.2f} conf={state.confidence:.2f}"


def day_month(value: date) -> str:
    """`5 окт` — the short date the context and the tutor use."""
    return f"{value.day} {_MONTHS[value.month - 1]}"


def _limit(name: str, topic_skill_id: str | None, params: KnowledgeParams) -> int:
    base = _LIMITS[name]
    if topic_skill_id is None:
        return math.ceil(base * params.context_set_multiplier)
    return base


def _topic_line(
    raw: GraphRaw,
    topic_skill_id: str,
    names: dict[str, str],
    extras: ContextExtras,
    params: KnowledgeParams,
    now: datetime,
) -> str:
    rows = {row.skill_id: row for row in raw.q1}
    name = names.get(topic_skill_id, topic_skill_id)
    row = rows.get(topic_skill_id)
    state = _fresh(row.state, now) if row else None
    if state is None or state.confidence < params.c_vis:
        line = f"{name}: мало данных"
    else:
        history = [_fresh(s, now) for s in row.history] if row else []
        trend = words.trend(
            sorted((s for s in history if s), key=lambda s: s.last_observed_at)
        )
        line = f"{name} — {_pc(state)} trend={trend}"
        due = due_at(state.last_observed_at, state.half_life_h, extras.p_target)
        days = (due - now).total_seconds() / 86400
        if days < _DUE_SOON_DAYS:
            line += (
                "; пора повторить"
                if days <= 0
                else f"; повторить через {max(1, math.ceil(days))} дн."
            )
    set_out = extras.set
    if set_out is not None:
        ordered = sorted(set_out.topics, key=lambda t: t.position)
        index = next(
            (i for i, t in enumerate(ordered) if t.skill_id == topic_skill_id), None
        )
        if index is not None:
            line += f"; в сете {index + 1} из {len(ordered)}"
            following = next(
                (t for t in ordered[index + 1 :] if t.status == "open"), None
            )
            if following is not None:
                line += f", дальше — {following.name}"
    return line


def _assemble(
    raw: GraphRaw,
    topic_skill_id: str | None,
    extras: ContextExtras,
    params: KnowledgeParams,
    now: datetime,
) -> TopicContext:
    rows = {row.skill_id: row for row in raw.q1}
    set_out = extras.set
    # The graph's skill name wins; the set's topic name only fills gaps (the
    # sets repository falls back to the skill id when it has no name).
    names = {t.skill_id: t.name for t in set_out.topics} if set_out else {}
    names.update({row.skill_id: row.name for row in raw.q1})
    set_topic_ids = {t.skill_id for t in set_out.topics} if set_out else set()

    def limit(name: str) -> int:
        return _limit(name, topic_skill_id, params)

    ctx = TopicContext(skill_ids=list(raw.skill_ids), as_of=now)
    placed: set[str] = set()

    if topic_skill_id is not None:
        ctx.topic_name = names.get(topic_skill_id, topic_skill_id)
        ctx.topic = [_topic_line(raw, topic_skill_id, names, extras, params, now)]
        placed.add(topic_skill_id)
    elif set_out is not None:
        ordered = sorted(set_out.topics, key=lambda t: t.position)
        ctx.topic_name = "сет"
        ctx.topic = ["сет: " + ", ".join(t.name for t in ordered)]
        placed.update(set_topic_ids)
    ctx.topic = ctx.topic[: limit("topic")]
    if set_out is not None:
        ctx.set_label = f"сет {set_out.position} до {day_month(set_out.deadline)}"

    # strengths — without the topic itself; the most reliable first (p·conf):
    # a skill the model is sure about is a better thing to lean on than a
    # slightly higher p with shaky confidence.
    strong = []
    for skill_id, row in rows.items():
        state = _fresh(row.state, now)
        if skill_id == topic_skill_id or state is None:
            continue
        if state.p_recall >= 0.8 and state.confidence >= 0.5:
            strong.append((state.p_recall * state.confidence, skill_id, state))
    strong.sort(key=lambda item: (-item[0], item[1]))
    for _, skill_id, state in strong[: limit("strengths")]:
        ctx.strengths.append(f"{names.get(skill_id, skill_id)}: {_pc(state)}")
        placed.add(skill_id)

    # prerequisite gaps — rooted ones first, then by p ascending
    gaps = []
    for skill_id, row in rows.items():
        state = _fresh(row.state, now)
        if skill_id in placed or skill_id in set_topic_ids or state is None:
            continue
        if state.p_recall < 0.6 and state.confidence > 0.5:
            n_roots = raw.q2.get(skill_id, (0, 0.0))[0]
            gaps.append((0 if n_roots else 1, state.p_recall, skill_id, state, n_roots))
    gaps.sort(key=lambda item: (item[0], item[1], item[2]))
    for _, _, skill_id, state, n_roots in gaps[: limit("prerequisite_gaps")]:
        line = f"{names.get(skill_id, skill_id)}: {_pc(state)}"
        if n_roots:
            line += f" (корень {n_roots} ошибок за {params.root_window_days} дней)"
        ctx.prerequisite_gaps.append(line)
        placed.add(skill_id)

    # misconceptions — suspected / disputed never reach the tutor (§11.1)
    confirmed = sorted(
        (
            m
            for m in raw.q3
            if m.status == "confirmed" and visible_to(m, "tutor", params, now)
        ),
        key=lambda m: (-m.occurrence_count, m.misconception_id),
    )
    for m in confirmed[: limit("active_misconceptions")]:
        note = f"подтверждено, {m.occurrence_count} набл."
        trigger = trigger_words(m.triggers or {}, params=params)
        if trigger:
            note += f"; {trigger}"
        ctx.active_misconceptions.append(f"{m.name} ({note})")
    watched = sorted(
        (
            m
            for m in raw.q3
            if m.status == "resolved" and visible_to(m, "tutor", params, now)
        ),
        key=lambda m: m.updated_at,
        reverse=True,
    )
    for m in watched[: limit("under_watch")]:
        ctx.under_watch.append(f"{m.name} (исправлено, следим)")

    # low data — everything not already placed above
    for skill_id in raw.skill_ids:
        if len(ctx.low_data) >= limit("low_data"):
            break
        if skill_id in placed:
            continue
        row = rows.get(skill_id)
        state = row.state if row else None
        if state is None or state.confidence < params.c_vis:
            ctx.low_data.append(f"{names.get(skill_id, skill_id)}: мало данных")
            placed.add(skill_id)

    deadline: list[str] = []
    if set_out is not None:
        deadline.append(f"сет до {day_month(set_out.deadline)}")
    upcoming = sorted(raw.q4, key=lambda d: d.date)
    if upcoming:
        first = upcoming[0]
        label = _EXAM_LABEL.get(first.exam_id, first.exam_id)
        deadline.append(f"{label} {day_month(first.date)}")
    ctx.deadline = deadline[: limit("deadline")]

    pace = extras.profile.questionnaire.pace
    lines: list[str] = []
    if pace.hint_level.value is not None:
        lines.append(f"подсказка уровня {_HINT_LEVEL[pace.hint_level.value]}")
    if pace.explanation_depth.value is not None:
        lines.append(f"объяснения {pace.explanation_depth.value}")
    if pace.hours_per_week.value is not None:
        lines.append(f"~{pace.hours_per_week.value} ч/нед")
    ctx.profile = lines[: limit("profile")]

    if extras.previous_summary:
        ctx.previous_set = [extras.previous_summary[:_PREVIOUS_SET_CHARS]][
            : limit("previous_set")
        ]
    return ctx


def _size(ctx: TopicContext) -> int:
    return sum(len(line) for name in SLOT_ORDER for line in getattr(ctx, name))


def _truncate(ctx: TopicContext, budget_chars: int) -> bool:
    """Cut lines from the bottom of the table until the slots fit the budget."""
    truncated = False
    for name in _TRUNCATE_ORDER:
        slot: list[str] = getattr(ctx, name)
        while slot and _size(ctx) > budget_chars:
            slot.pop()
            truncated = True
        if _size(ctx) <= budget_chars:
            break
    return truncated


def slots(ctx: TopicContext) -> dict[str, Any]:
    """Slots in the fixed order (logging, rendering)."""
    return {name: list(getattr(ctx, name)) for name in SLOT_ORDER}
