"""The facts of a finished set — §4.2.

Pure: the numbers are computed here, inside the `set.completed` transaction,
and the model only puts them into a sentence. If the model never answers,
the Overview still shows everything below (product-logic §6.3).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import KnowledgeParams
from app.knowledge.words import skill_level
from app.schemas.common import ExamId, SkillLevel
from app.schemas.knowledge import ForecastOut, KnowledgeStateOut, MisconceptionStateOut
from app.schemas.sets import (
    MisconceptionBrief,
    NextSetBrief,
    SetStats,
    SkillDelta,
)

_PRIOR_P_RECALL = 0.5


class SkillHistory(BaseModel):
    """One skill of the set: where it stood when the set opened, and now."""

    skill_id: str
    name: str
    before: KnowledgeStateOut | None = None
    after: KnowledgeStateOut | None = None
    closed: bool = False


class ReportInputs(BaseModel):
    set_id: UUID
    exam_id: ExamId
    kind: str = "regular"
    opened_at: datetime | None = None
    completed_at: datetime | None = None
    deadline: date
    tasks_answered: int = 0
    tasks_correct: int = 0
    mocks_completed: int = 0
    skills: list[SkillHistory] = Field(default_factory=list)
    misconceptions: list[MisconceptionStateOut] = Field(default_factory=list)
    p_target: float = 0.9
    forecast_before: ForecastOut | None = None
    forecast_after: ForecastOut | None = None
    next_set: NextSetBrief | None = None
    previous_summary_id: UUID | None = None


def set_stats(inputs: ReportInputs, params: KnowledgeParams, now: datetime) -> SetStats:
    """Everything the report may speak about, and nothing else."""
    completed = inputs.completed_at or now
    opened = inputs.opened_at
    days_in_set = max(0, (completed.date() - opened.date()).days) if opened else 0
    days_vs_deadline = (inputs.deadline - completed.date()).days

    deltas = [_delta(item, inputs.p_target, params) for item in inputs.skills]
    growth = sorted(deltas, key=lambda item: item.delta_p, reverse=True)
    top_growth = [
        item.skill_id
        for item in growth[: params.summary_top_growth]
        if item.delta_p > 0
    ]

    resolved, watching, new_confirmed = _misconceptions(inputs, opened, completed)

    ready_shift: int | None = None
    before, after = inputs.forecast_before, inputs.forecast_after
    if before is not None and after is not None:
        if before.ready_by is not None and after.ready_by is not None:
            # Плюс — стал готов раньше, чем обещал прогноз на входе в сет.
            ready_shift = (before.ready_by - after.ready_by).days

    return SetStats(
        set_id=inputs.set_id,
        exam_id=inputs.exam_id,
        kind=inputs.kind,  # type: ignore[arg-type]
        opened_at=opened,
        completed_at=completed,
        deadline=inputs.deadline,
        days_in_set=days_in_set,
        days_vs_deadline=days_vs_deadline,
        tasks_answered=inputs.tasks_answered,
        tasks_correct=inputs.tasks_correct,
        mocks_completed=inputs.mocks_completed,
        skills_total=len(inputs.skills),
        skills_closed=sum(1 for item in inputs.skills if item.closed),
        skills=deltas,
        top_growth=top_growth,
        misconceptions_resolved=resolved,
        misconceptions_still_watching=watching,
        misconceptions_new_confirmed=new_confirmed,
        forecast_before=before,
        forecast_after=after,
        on_track_after=after.on_track if after is not None else None,
        ready_by_shift_days=ready_shift,
        next_set=inputs.next_set,
        previous_summary_id=inputs.previous_summary_id,
    )


def stats_words(stats: SetStats) -> str:
    """Two or three facts in words — the tutor's `previous_set` slot when the
    text is missing (§4.5)."""
    parts: list[str] = []
    if stats.skills_closed:
        parts.append(f"закрыто тем: {stats.skills_closed} из {stats.skills_total}")
    if stats.tasks_answered:
        parts.append(
            f"решено задач: {stats.tasks_answered}, верно {stats.tasks_correct}"
        )
    grown = [delta.name for delta in stats.skills if delta.skill_id in stats.top_growth]
    if grown:
        parts.append("сильнее всего выросли: " + ", ".join(grown))
    if stats.misconceptions_resolved:
        parts.append(
            "исправлено: "
            + ", ".join(item.name for item in stats.misconceptions_resolved)
        )
    if stats.misconceptions_still_watching:
        parts.append(
            "следим за: "
            + ", ".join(item.name for item in stats.misconceptions_still_watching)
        )
    if stats.on_track_after is True:
        parts.append("к тесту успеваешь")
    elif stats.on_track_after is False:
        parts.append("к тесту пока не успеваешь")
    return "; ".join(parts) if parts else "по сету пока нечего рассказать"


# --- internals ---


def _p(state: KnowledgeStateOut | None) -> float:
    return state.p_recall if state is not None else _PRIOR_P_RECALL


def _level(
    state: KnowledgeStateOut | None, p_target: float, params: KnowledgeParams
) -> SkillLevel:
    return skill_level(state, p_target, params)


def _delta(item: SkillHistory, p_target: float, params: KnowledgeParams) -> SkillDelta:
    p_before, p_after = _p(item.before), _p(item.after)
    return SkillDelta(
        skill_id=item.skill_id,
        name=item.name,
        level_before=_level(item.before, p_target, params),
        level_after=_level(item.after, p_target, params),
        p_before=p_before,
        p_after=p_after,
        delta_p=round(p_after - p_before, 6),
    )


def _misconceptions(
    inputs: ReportInputs, opened: datetime | None, completed: datetime
) -> tuple[
    list[MisconceptionBrief], list[MisconceptionBrief], list[MisconceptionBrief]
]:
    resolved: list[MisconceptionBrief] = []
    watching: list[MisconceptionBrief] = []
    new_confirmed: list[MisconceptionBrief] = []
    for state in inputs.misconceptions:
        brief = MisconceptionBrief(id=state.misconception_id, name=state.name)
        in_window = _in_window(state.updated_at, opened, completed)
        if state.status == "resolved":
            if in_window:
                resolved.append(brief)
            continue
        if state.status == "disputed":
            continue
        if state.status == "confirmed" and _in_window(
            state.first_seen_at, opened, completed
        ):
            new_confirmed.append(brief)
        watching.append(brief)
    return resolved, watching, new_confirmed


def _in_window(moment: datetime, opened: datetime | None, completed: datetime) -> bool:
    if opened is None:
        return moment <= completed
    return opened <= moment <= completed
