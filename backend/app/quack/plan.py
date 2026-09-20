"""Planning the Quack feed — product-logic §3.6, ТЗ §8.2.

Pure and deterministic: the same inputs always produce the same drafts in
the same order, with the same `reason_hash`. The hash *is* the identity of a
cause — a decline suppresses it until one of its parameters changes, and a
cause that disappears expires the row that carried it.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import KnowledgeParams
from app.roadmap.milestones import exam_label, format_date_ru
from app.schemas.knowledge import ForecastOut
from app.schemas.matching import MatchOut
from app.schemas.profile import Profile
from app.schemas.programs import Program
from app.schemas.quack import (
    PaceVariantOut,
    RecDraft,
    RecommendationAction,
    StudentAggregates,
    Urgency,
    urgency_rank,
)
from app.schemas.roadmap import ConflictOut, ExamRequirementOut, MilestoneOut
from app.schemas.sets import SetsByExam

_KIND_ORDER = (
    "pace_variant",
    "conflict",
    "milestone_due",
    "next_set",
    "set_change",
    "program_new_fit",
    "saved_realism_shift",
    "diagnostic_suggested",
    "activity_pause",
)
_FAR_FUTURE = date(9999, 12, 31)


class PlanInputs(BaseModel):
    """What the planner sees — collected by `apply.quack.collect_inputs`."""

    today: date
    profile: Profile
    saved: list[Program] = Field(default_factory=list)
    requirements: list[ExamRequirementOut] = Field(default_factory=list)
    milestones: list[MilestoneOut] = Field(default_factory=list)
    conflicts: list[ConflictOut] = Field(default_factory=list)
    forecasts: dict[str, ForecastOut] = Field(default_factory=dict)
    pace_variants: dict[str, list[PaceVariantOut]] = Field(default_factory=dict)
    sets_by_exam: dict[str, SetsByExam] = Field(default_factory=dict)
    matching_now: list[MatchOut] = Field(default_factory=list)
    matching_prev: list[dict[str, Any]] | None = None
    aggregates: StudentAggregates | None = None
    open_recs: list[Any] = Field(default_factory=list)
    declined_hashes: set[str] = Field(default_factory=set)
    previous_upcoming: dict[str, list[str]] = Field(default_factory=dict)


def reason_hash(kind: str, **key: Any) -> str:
    """Stable identity of a cause: kind plus its distinguishing parameters."""
    payload = json.dumps(
        {"kind": kind, **{name: _plain(value) for name, value in sorted(key.items())}},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _plain(value: Any) -> Any:
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list | tuple | set):
        return sorted((_plain(item) for item in value), key=str)
    if isinstance(value, dict):
        return {str(name): _plain(item) for name, item in sorted(value.items())}
    if isinstance(value, float):
        return round(value, 4)
    return value


def plan(inputs: PlanInputs, params: KnowledgeParams, today: date) -> list[RecDraft]:
    """Every rule of the §8.2 table, ordered and numbered."""
    drafts: list[RecDraft] = []
    drafts += _pace_variants(inputs, params)
    drafts += _conflicts(inputs)
    drafts += _milestones(inputs, params, today)
    drafts += _sets(inputs)
    drafts += _programs(inputs)
    drafts += _diagnostic(inputs)

    has_pace = any(draft.kind == "pace_variant" for draft in drafts)
    drafts += _activity_pause(inputs, today, has_pace)

    # Отказ уважается, пока не изменилась причина (причина = хэш).
    drafts = [
        draft for draft in drafts if draft.reason_hash not in inputs.declined_hashes
    ]
    drafts = _dedupe(drafts)
    # Порядок создания — последний признак сортировки: при равной срочности
    # и дате правила идут в порядке таблицы §8.2, а внутри правила — в том,
    # в каком их выдал расчёт (варианты темпа, вехи одного дня).
    created = {id(draft): index for index, draft in enumerate(drafts)}
    drafts.sort(key=lambda draft: _sort_key(draft, today, created[id(draft)]))
    drafts = _trim(drafts, params.quack_feed_limit)
    for position, draft in enumerate(drafts):
        draft.position = position
    return drafts


# --- rules ---


def _pace_variants(inputs: PlanInputs, params: KnowledgeParams) -> list[RecDraft]:
    """`on_track is False` → one draft per available way out (§8.3).

    Urgency is `urgent` by product-logic §8.5: the forecast already says the
    student will not be ready in time, and that is the one thing Quack is
    allowed to interrupt for.
    """
    del params
    out: list[RecDraft] = []
    for exam_id, forecast in sorted(inputs.forecasts.items()):
        if forecast.on_track is not False:
            continue
        for variant in inputs.pace_variants.get(exam_id, []):
            if not variant.available:
                continue
            out.append(
                RecDraft(
                    kind="pace_variant",
                    urgency="urgent",
                    title=f"{exam_label(exam_id)}: {_variant_title(variant.kind)}",
                    reason=_pace_reason(exam_id, forecast),
                    action_text=variant.text,
                    action=_variant_action(exam_id, variant),
                    reason_hash=reason_hash(
                        "pace",
                        exam_id=exam_id,
                        variant=variant.kind,
                        params=variant.params,
                    ),
                    exam_id=exam_id,  # type: ignore[arg-type]
                    program_id=variant.params.get("program_id"),
                    forecast_after=variant.forecast,
                )
            )
    return out


def _variant_title(kind: str) -> str:
    return {
        "more_hours": "добавить часы",
        "move_date": "перенести тест",
        "remove_program": "убрать программу",
        "lower_target": "снизить цель",
    }.get(kind, kind)


def _pace_reason(exam_id: str, forecast: ForecastOut) -> str:
    ready = format_date_ru(forecast.ready_by) if forecast.ready_by else "позже теста"
    test = format_date_ru(forecast.test_date) if forecast.test_date else "неизвестно"
    return (
        f"{exam_label(exam_id)}: готовность {ready}, тест {test} — к сроку не выходит"
    )


def _variant_action(exam_id: str, variant: PaceVariantOut) -> RecommendationAction:
    if variant.kind == "more_hours":
        return RecommendationAction(
            kind="profile_update",
            profile_path="pace.hours_per_week",
            profile_value=variant.params.get("hours_per_week"),
        )
    if variant.kind == "move_date":
        test_date = variant.params.get("test_date")
        if test_date is None:
            return RecommendationAction(kind="acknowledge")
        return RecommendationAction(
            kind="requirement_update",
            exam_id=exam_id,  # type: ignore[arg-type]
            test_date=date.fromisoformat(str(test_date)),
        )
    if variant.kind == "remove_program":
        return RecommendationAction(
            kind="program_remove", program_id=variant.params.get("program_id")
        )
    if variant.kind == "lower_target":
        return RecommendationAction(
            kind="requirement_update",
            exam_id=exam_id,  # type: ignore[arg-type]
            target_score=float(variant.params["target_score"]),
        )
    return RecommendationAction(kind="acknowledge")


def _conflicts(inputs: PlanInputs) -> list[RecDraft]:
    out: list[RecDraft] = []
    for conflict in inputs.conflicts:
        options = list(conflict.options)
        if conflict.kind == "exam_after_deadline":
            options = [*options, "перенести тест — вариант темпа в Quack"]
        out.append(
            RecDraft(
                kind="conflict",
                urgency="urgent",
                title="Конфликт в плане",
                reason=conflict.text,
                action_text="; ".join(options) if options else "выбери, что сдвинуть",
                action=RecommendationAction(kind="acknowledge"),
                reason_hash=reason_hash(
                    "conflict",
                    conflict_kind=conflict.kind,
                    milestone_keys=sorted(conflict.milestone_keys),
                ),
            )
        )
    return out


def _milestone_urgency(days: int, params: KnowledgeParams) -> Urgency | None:
    if days <= params.urgent_milestone_days:
        return "urgent"
    if days <= 14:
        return "high"
    if days <= 30:
        return "normal"
    return None


def _milestones(
    inputs: PlanInputs, params: KnowledgeParams, today: date
) -> list[RecDraft]:
    out: list[RecDraft] = []
    for milestone in inputs.milestones:
        if milestone.done:
            continue
        days = (milestone.date - today).days
        if days < 0:
            continue
        urgency = _milestone_urgency(days, params)
        if urgency is None:
            continue
        out.append(
            RecDraft(
                kind="milestone_due",
                urgency=urgency,
                title=milestone.title,
                reason=f"срок {format_date_ru(milestone.date)}",
                action_text="открыть и отметить, когда сделано",
                action=RecommendationAction(
                    kind="milestone_open", milestone_key=milestone.key
                ),
                reason_hash=reason_hash("milestone", key=milestone.key),
                exam_id=milestone.exam_id,
                program_id=milestone.program_id,
                milestone_key=milestone.key,
                expires_at=datetime.combine(
                    milestone.date, datetime.min.time(), tzinfo=UTC
                ),
            )
        )
    return out


def _sets(inputs: PlanInputs) -> list[RecDraft]:
    out: list[RecDraft] = []
    for exam_id, sets in sorted(inputs.sets_by_exam.items()):
        if sets.current is None and sets.upcoming:
            nxt = sets.upcoming[0]
            out.append(
                RecDraft(
                    kind="next_set",
                    urgency="high",
                    title="Следующий сет готов",
                    reason=nxt.reason or "предыдущий сет закрыт",
                    action_text="открыть сет",
                    action=RecommendationAction(kind="set_open", set_id=nxt.id),
                    reason_hash=reason_hash("next_set", set_id=nxt.id),
                    exam_id=exam_id,  # type: ignore[arg-type]
                )
            )
        out += _set_change(inputs, exam_id, sets)
    return out


def _set_change(inputs: PlanInputs, exam_id: str, sets: SetsByExam) -> list[RecDraft]:
    out: list[RecDraft] = []
    if sets.upcoming:
        nxt = sets.upcoming[0]
        skill_ids = sorted(topic.skill_id for topic in nxt.topics)
        previous = inputs.previous_upcoming.get(exam_id)
        if previous is not None and sorted(previous) != skill_ids:
            out.append(
                RecDraft(
                    kind="set_change",
                    urgency="normal",
                    title="Состав следующего сета изменился",
                    reason="план пересобран по новым данным модели знаний",
                    action_text="посмотреть и поправить, если нужно",
                    action=RecommendationAction(
                        kind="set_edit", set_id=nxt.id, skill_ids=skill_ids
                    ),
                    reason_hash=reason_hash(
                        "set_change", set_id=nxt.id, skill_ids=skill_ids
                    ),
                    exam_id=exam_id,  # type: ignore[arg-type]
                )
            )
    current = sets.current
    if current is not None and current.deadline < inputs.today:
        out.append(
            RecDraft(
                kind="set_change",
                urgency="normal",
                title="Дедлайн текущего сета прошёл",
                reason=f"срок был {format_date_ru(current.deadline)}",
                action_text="сдвинуть дедлайн или закрыть темы",
                action=RecommendationAction(
                    kind="set_edit", set_id=current.id, deadline=inputs.today
                ),
                reason_hash=reason_hash(
                    "set_change",
                    set_id=current.id,
                    skill_ids=sorted(t.skill_id for t in current.topics),
                    deadline_passed=True,
                ),
                exam_id=exam_id,  # type: ignore[arg-type]
            )
        )
    return out


def _programs(inputs: PlanInputs) -> list[RecDraft]:
    out: list[RecDraft] = []
    previous = {
        str(item.get("program_id")): str(item.get("realism"))
        for item in (inputs.matching_prev or [])
    }
    saved_ids = {program.id for program in inputs.saved}
    for match in inputs.matching_now:
        program_id = match.program.id
        realism = match.realism
        was = previous.get(program_id)
        if realism in ("possible", "try") and was not in ("possible", "try"):
            if inputs.matching_prev is not None and program_id not in saved_ids:
                out.append(
                    RecDraft(
                        kind="program_new_fit",
                        urgency="normal",
                        title=f"{match.program.university} стала подходить",
                        reason=f"уровень реалистичности: {_realism_words(realism)}",
                        action_text="посмотреть карточку",
                        action=RecommendationAction(kind="acknowledge"),
                        reason_hash=reason_hash(
                            "new_fit", program_id=program_id, realism=realism
                        ),
                        program_id=program_id,
                    )
                )
        if program_id in saved_ids and was is not None and was != realism:
            worse = _realism_rank(realism) > _realism_rank(was)
            out.append(
                RecDraft(
                    kind="saved_realism_shift",
                    urgency="high" if worse else "normal",
                    title=f"{match.program.university}: шансы изменились",
                    reason=(
                        f"было {_realism_words(was)}, стало {_realism_words(realism)}"
                    ),
                    action_text="посмотреть, какие факторы сдвинулись",
                    action=RecommendationAction(kind="acknowledge"),
                    reason_hash=reason_hash(
                        "shift",
                        program_id=program_id,
                        from_realism=was,
                        to_realism=realism,
                    ),
                    program_id=program_id,
                )
            )
    return out


def _realism_rank(value: str) -> int:
    return {"possible": 0, "try": 1, "impossible": 2}.get(value, 3)


def _realism_words(value: str) -> str:
    return {
        "possible": "реально",
        "try": "стоит попробовать",
        "impossible": "пока нереально",
    }.get(value, value)


def _diagnostic(inputs: PlanInputs) -> list[RecDraft]:
    out: list[RecDraft] = []
    measured: set[str] = {
        exam_id
        for exam_id, forecast in inputs.forecasts.items()
        if forecast.coverage > 0
    }
    for requirement in inputs.requirements:
        if not requirement.has_knowledge_model or requirement.exam_id in measured:
            continue
        out.append(
            RecDraft(
                kind="diagnostic_suggested",
                urgency="normal",
                title=f"{exam_label(requirement.exam_id)}: сделать замер",
                reason="без замера прогноз считается по твоей оценке",
                action_text="пройти короткий замер",
                action=RecommendationAction(kind="acknowledge"),
                reason_hash=reason_hash("diag", exam_id=requirement.exam_id),
                exam_id=requirement.exam_id,
            )
        )
    return out


def _activity_pause(inputs: PlanInputs, today: date, has_pace: bool) -> list[RecDraft]:
    """No reproach: the pause matters only because the forecast moved (§8.2)."""
    aggregates = inputs.aggregates
    if aggregates is None or aggregates.active_days != 0:
        return []
    if not any(sets.current is not None for sets in inputs.sets_by_exam.values()):
        return []
    if has_pace:
        return []
    iso_week = f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"
    return [
        RecDraft(
            kind="activity_pause",
            urgency="low",
            title="Пауза в занятиях",
            reason="прогноз пересчитан с учётом паузы",
            action_text="посмотреть, что изменить в темпе",
            action=RecommendationAction(kind="acknowledge"),
            reason_hash=reason_hash("pause", iso_week=iso_week),
        )
    ]


# --- ordering ---


def _dedupe(drafts: list[RecDraft]) -> list[RecDraft]:
    seen: set[str] = set()
    out: list[RecDraft] = []
    for draft in drafts:
        if draft.reason_hash in seen:
            continue
        seen.add(draft.reason_hash)
        out.append(draft)
    return out


def _sort_key(draft: RecDraft, today: date, created: int) -> tuple[int, date, int, int]:
    when = _FAR_FUTURE
    if draft.expires_at is not None:
        when = draft.expires_at.date()
    elif draft.forecast_after is not None and draft.forecast_after.test_date:
        when = draft.forecast_after.test_date
    return (
        urgency_rank(draft.urgency),
        max(when, today),
        _KIND_ORDER.index(draft.kind) if draft.kind in _KIND_ORDER else 99,
        created,
    )


def _trim(drafts: list[RecDraft], limit: int) -> list[RecDraft]:
    """`urgent`/`high` are never dropped; the quiet tail is."""
    keep = [draft for draft in drafts if draft.urgency in ("urgent", "high")]
    rest = [draft for draft in drafts if draft.urgency not in ("urgent", "high")]
    room = max(0, limit - len(keep))
    kept = {id(draft) for draft in [*keep, *rest[:room]]}
    return [draft for draft in drafts if id(draft) in kept]


__all__ = ["PlanInputs", "plan", "reason_hash"]
