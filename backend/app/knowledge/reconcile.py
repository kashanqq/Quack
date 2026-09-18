"""Reconcile a task answer — memory-architecture-quack.md §8.2, steps 2–8.

Pure function: takes the instance, the grade, the current state and returns
the new evidence, state, misconception change and root causes. No I/O.

Source: 20-B1-phase2.md §2.1.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.config import KnowledgeParams
from app.knowledge import hlr, weights
from app.knowledge.misconceptions import next_status
from app.knowledge.roots import rule_root
from app.knowledge.words import state_words
from app.schemas.events import TaskAnsweredPayload
from app.schemas.knowledge import (
    EvidenceContext,
    EvidenceIn,
    ExamId,
    KnowledgeStateOut,
    MisconceptionChange,
    MisconceptionStateOut,
    Prerequisite,
    ReconcileResult,
)
from app.schemas.tasks import Grade, TaskInstance

if TYPE_CHECKING:
    from app.schemas.knowledge import RootCauseOut


_MOCK_MODES = {"mock_set", "mock_topic", "mock_misconception"}


def reconcile_task_answer(
    instance: TaskInstance,
    grade: Grade,
    payload: TaskAnsweredPayload,
    state: KnowledgeStateOut | None,
    prereq_states: list[tuple[Prerequisite, KnowledgeStateOut | None]],
    misc_states: list[MisconceptionStateOut],
    n_seen: int,
    exam_ids: list[ExamId],
    params: KnowledgeParams,
    now: datetime,
    event_id: int | None = None,
) -> ReconcileResult:
    """Apply one task answer (§8.2 steps 3–8).

    Steps 1 (event) and 9–10 (persistence, rebuild) are done by apply/*.
    """
    # --- direction / share ---
    if grade.correct:
        direction: int = 1
        share: float | None = None
    elif grade.partial is not None:
        direction = 0
        share = grade.partial
    else:
        direction = -1
        share = None

    # --- source / tier from mode ---
    mode = payload.mode
    if mode in _MOCK_MODES:
        source = "mock"
    elif mode == "diagnostic":
        source = "diagnostic"
    elif mode == "chat":
        source = "chat"
    else:
        source = "task"

    tier = weights.tier_for(source, mode, kind=None)

    # --- matched (по ТЗ §8.2 п.3 — только для неверного без совпадения) ---
    matched = grade.correct or grade.matched_misconception_id is not None

    weight = weights.evidence_weight(
        source,
        mode,
        None,
        seen_before=n_seen > 0,
        matched=matched,
        params=params,
    )

    df = hlr.difficulty_factor(instance.difficulty)

    ctx = EvidenceContext(
        task_type=instance.type,
        difficulty=instance.difficulty,
        tags=instance.tags or None,
        mode=payload.mode,
        time_ratio=payload.time_spent_sec / max(1, instance.time_reference_sec),
        session_minute=payload.session_minute,
        after_guideline=payload.after_guideline,
        hint_level_before=payload.hint_level_before,
        topic_skill_id=instance.skill_id,
        session_id=None,
    )

    ev_fields: dict = dict(
        event_id=event_id or 0,
        skill_id=instance.skill_id,
        exam_id=instance.exam_id,
        kind="task",
        tier=tier,
        source=source,
        weight=weight,
        direction=direction,
        share=share,
        difficulty_factor=df,
        summary=None,
        context=ctx,
        observed_at=now,
        extractor_version=None,
    )
    primary_ev = EvidenceIn(**ev_fields)
    evidence: list[EvidenceIn] = [primary_ev]

    # --- second evidence: misconception_hit ---
    if grade.matched_misconception_id is not None:
        misc_name = _misc_name(misc_states, grade.matched_misconception_id)
        evidence.append(
            EvidenceIn(
                **{**ev_fields, "kind": "misconception_hit", "summary": misc_name}
            )
        )

    # --- state ---
    state_after = hlr.apply_evidence(state, primary_ev, params=params)

    # --- cross-exam state for common skills (§4.6) ---
    cross_exam_state: KnowledgeStateOut | None = None
    if len(exam_ids) > 1 and instance.skill_id.startswith("math."):
        other_exam = next((e for e in exam_ids if e != instance.exam_id), None)
        if other_exam is not None:
            cross_ev = primary_ev.model_copy(
                update={
                    "exam_id": other_exam,
                    "weight": primary_ev.weight * params.transfer_cross_exam,
                }
            )
            cross = hlr.apply_evidence(None, cross_ev, params=params)
            cross_exam_state = cross.model_copy(
                update={"exam_id": other_exam, "has_strong": False}
            )

    # --- misconception change ---
    misconception_change = _apply_misconception(
        instance, grade, tier, misc_states, params
    )

    # --- root causes ---
    root_causes: list[RootCauseOut] = []
    if direction == -1:
        root = rule_root(instance.skill_id, prereq_states, params)
        if root is not None:
            root_causes.append(root.model_copy(update={"created_at": now}))

    # --- words ---
    words = state_words(state_after, params.p_target_max, params)

    return ReconcileResult(
        evidence=evidence,
        state_after=state_after,
        cross_exam_state=cross_exam_state,
        misconception_change=misconception_change,
        root_causes=root_causes,
        words=words,
    )


def _misc_name(states: list[MisconceptionStateOut], misc_id: str) -> str:
    for m in states:
        if m.misconception_id == misc_id:
            return m.name
    return misc_id


def _tested_misconceptions(instance: TaskInstance) -> set[str]:
    ids: set[str] = set()
    for opt in instance.options:
        if opt.misconception_id:
            ids.add(opt.misconception_id)
    for t in instance.trap_answers:
        if t.misconception_id:
            ids.add(t.misconception_id)
    return ids


def _apply_misconception(
    instance: TaskInstance,
    grade: Grade,
    tier: int,
    misc_states: list[MisconceptionStateOut],
    params: KnowledgeParams,
) -> MisconceptionChange | None:
    """Return the change of one MisconceptionState, if any."""
    strong = weights.is_strong(tier)  # type: ignore[arg-type]

    # 1) hit — новый matched, подтверждаем/создаём
    if grade.matched_misconception_id is not None:
        existing = next(
            (
                m
                for m in misc_states
                if m.misconception_id == grade.matched_misconception_id
            ),
            None,
        )
        if existing is None:
            return MisconceptionChange(
                misconception_id=grade.matched_misconception_id,
                from_status=None,
                to_status="suspected",
                counters={
                    "occurrence_count": 1,
                    "strong_count": int(strong),
                    "consecutive_avoided": 0,
                },
            )

        occ = existing.occurrence_count + 1
        strong_count = existing.strong_count + (1 if strong else 0)
        new_status = next_status(
            existing.status,
            event="hit",
            strong=strong,
            occurrence_count=occ,
            strong_count=strong_count,
            consecutive_avoided=0,
            strong_at_dispute=existing.strong_count,
            disputed_at=None,
            previous_status=existing.status,
            params=params,
        )
        return MisconceptionChange(
            misconception_id=existing.misconception_id,
            from_status=existing.status,
            to_status=new_status,
            counters={
                "occurrence_count": occ,
                "strong_count": strong_count,
                "consecutive_avoided": 0,
            },
        )

    # 2) avoided — верный ответ при наличии TRAPS на confirmed
    if grade.correct:
        tested = _tested_misconceptions(instance)
        for m in misc_states:
            if m.status == "confirmed" and m.misconception_id in tested:
                avoided = m.consecutive_avoided + 1
                new_status = next_status(
                    "confirmed",
                    event="avoided",
                    strong=False,
                    occurrence_count=m.occurrence_count,
                    strong_count=m.strong_count,
                    consecutive_avoided=avoided,
                    strong_at_dispute=m.strong_count,
                    disputed_at=None,
                    previous_status="confirmed",
                    params=params,
                )
                return MisconceptionChange(
                    misconception_id=m.misconception_id,
                    from_status="confirmed",
                    to_status=new_status,
                    counters={
                        "occurrence_count": m.occurrence_count,
                        "strong_count": m.strong_count,
                        "consecutive_avoided": avoided,
                    },
                )

    return None
