"""Reconcile task.answered — memory-architecture-quack.md §8.2, steps 2–8.

Numbers from 20-B1-phase2.md §8 (test_reconcile block).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import KnowledgeParams
from app.knowledge.reconcile import reconcile_task_answer
from app.schemas.events import TaskAnsweredPayload
from app.schemas.knowledge import (
    KnowledgeStateOut,
    MisconceptionStateOut,
    Prerequisite,
)
from app.schemas.tasks import Grade, Option, TaskInstance

pytestmark = pytest.mark.phase1

PARAMS = KnowledgeParams()
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _instance(
    *,
    type: str = "mcq4",
    skill_id: str = "math.alg.abs_value_eq",
    exam_id: str = "SAT_MATH",
    difficulty: int = 3,
    time_reference_sec: int = 60,
    options: list[Option] | None = None,
    trap_answers: list[Option] | None = None,
    tags: list[str] | None = None,
) -> TaskInstance:
    if options is None:
        options = [
            Option(key="A", text="correct", correct=True, misconception_id=None),
            Option(
                key="B",
                text="d1",
                correct=False,
                misconception_id="lib.abs_single_branch",
            ),
            Option(key="C", text="d2", correct=False, misconception_id=None),
            Option(key="D", text="d3", correct=False, misconception_id=None),
        ]
    return TaskInstance(
        id=uuid4(),
        template_id="tpl.test",
        seed=1,
        exam_id=exam_id,  # type: ignore[arg-type]
        type=type,  # type: ignore[arg-type]
        skill_id=skill_id,
        stem_rendered="...",
        options=options,
        answer="A",
        trap_answers=trap_answers or [],
        solution_rendered=["..."],
        figure_url=None,
        time_reference_sec=time_reference_sec,
        difficulty=difficulty,
        tags=tags or [],
    )


def _payload(*, mode: str = "topic", session_minute: int = 5) -> TaskAnsweredPayload:
    return TaskAnsweredPayload(
        instance_id=uuid4(),
        answer="A",
        time_spent_sec=30,
        mode=mode,  # type: ignore[arg-type]
        session_minute=session_minute,
        after_guideline=False,
        hint_level_before=0,
    )


def _correct() -> Grade:
    return Grade(correct=True)


def _wrong(misc_id: str | None = None) -> Grade:
    return Grade(correct=False, matched_misconception_id=misc_id)


def _partial(share: float) -> Grade:
    return Grade(correct=False, partial=share)


def _state(
    skill_id: str = "math.alg.abs_value_eq",
    exam_id: str = "SAT_MATH",
) -> KnowledgeStateOut:
    return KnowledgeStateOut(
        skill_id=skill_id,
        exam_id=exam_id,  # type: ignore[arg-type]
        p_recall=0.5,
        p_at_obs=0.5,
        half_life_h=24.0,
        confidence=0.5,
        evidence_mass=1.0,
        n_correct=1,
        n_incorrect=0,
        n_partial=0,
        has_strong=True,
        last_observed_at=NOW - timedelta(hours=1),
        created_at=NOW - timedelta(days=1),
    )


def _misc(
    status: str = "suspected",
    *,
    occ: int = 1,
    strong: int = 0,
    avoided: int = 0,
) -> MisconceptionStateOut:
    return MisconceptionStateOut(
        misconception_id="lib.abs_single_branch",
        name="Раскрытие модуля только в одной ветви",
        status=status,  # type: ignore[arg-type]
        occurrence_count=occ,
        strong_count=strong,
        consecutive_avoided=avoided,
        triggers={},
        first_seen_at=NOW - timedelta(days=1),
        updated_at=NOW - timedelta(hours=1),
        skill_ids=["math.alg.abs_value_eq"],
    )


# --- tests ---


def test_reconcile_correct_mock_tier_1_grows_h_by_alpha():
    inst = _instance()
    payload = _payload(mode="mock_set")
    result = reconcile_task_answer(
        inst,
        _correct(),
        payload,
        None,
        [],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
        event_id=42,
    )
    assert len(result.evidence) == 1
    ev = result.evidence[0]
    assert ev.tier == 1
    assert ev.direction == 1
    assert ev.event_id == 42
    assert result.state_after.half_life_h == pytest.approx(48.0)
    assert result.state_after.n_correct == 1
    assert result.state_after.has_strong is True


def test_reconcile_wrong_with_distractor_makes_two_evidences():
    inst = _instance()
    payload = _payload(mode="topic")
    result = reconcile_task_answer(
        inst,
        _wrong("lib.abs_single_branch"),
        payload,
        None,
        [],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    assert len(result.evidence) == 2
    kinds = {e.kind for e in result.evidence}
    assert kinds == {"task", "misconception_hit"}
    # Разные ordinal — иначе MERGE в графе схлопнул бы их в один узел
    by_kind = {e.kind: e for e in result.evidence}
    assert by_kind["task"].ordinal == 0
    assert by_kind["misconception_hit"].ordinal == 1
    assert by_kind["task"].event_id == by_kind["misconception_hit"].event_id
    assert result.misconception_change is not None
    assert result.misconception_change.from_status is None
    assert result.misconception_change.to_status == "suspected"


def test_reconcile_second_strong_hit_confirms():
    inst = _instance()
    payload = _payload(mode="topic")
    existing = _misc("suspected", occ=1, strong=1)
    result = reconcile_task_answer(
        inst,
        _wrong("lib.abs_single_branch"),
        payload,
        None,
        [],
        [existing],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    assert result.misconception_change is not None
    assert result.misconception_change.from_status == "suspected"
    assert result.misconception_change.to_status == "confirmed"


def test_reconcile_correct_avoided_resolves_confirmed():
    inst = _instance()  # has an option with lib.abs_single_branch → task tests it
    payload = _payload(mode="topic")
    existing = _misc("confirmed", occ=3, strong=1, avoided=2)
    result = reconcile_task_answer(
        inst,
        _correct(),
        payload,
        None,
        [],
        [existing],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    assert result.misconception_change is not None
    assert result.misconception_change.from_status == "confirmed"
    assert result.misconception_change.to_status == "resolved"
    assert result.misconception_change.counters["consecutive_avoided"] == 3


def test_reconcile_common_skill_gives_cross_exam_state():
    inst = _instance(skill_id="math.alg.abs_value_eq", exam_id="SAT_MATH")
    payload = _payload(mode="mock_set")
    result = reconcile_task_answer(
        inst,
        _correct(),
        payload,
        None,
        [],
        [],
        0,
        ["SAT_MATH", "ENT_MATH"],
        PARAMS,
        NOW,
    )
    assert result.cross_exam_state is not None
    assert result.cross_exam_state.exam_id == "ENT_MATH"
    assert result.cross_exam_state.has_strong is False


def test_reconcile_seen_template_reduces_weight():
    inst = _instance()
    payload = _payload(mode="topic")
    fresh = reconcile_task_answer(
        inst, _correct(), payload, None, [], [], 0, ["SAT_MATH"], PARAMS, NOW
    )
    seen = reconcile_task_answer(
        inst, _correct(), payload, None, [], [], 1, ["SAT_MATH"], PARAMS, NOW
    )
    assert fresh.evidence[0].weight == pytest.approx(0.8)
    assert seen.evidence[0].weight == pytest.approx(0.8 * 0.8)


def test_reconcile_unmatched_wrong_reduces_weight():
    inst = _instance()
    payload = _payload(mode="topic")
    result = reconcile_task_answer(
        inst, _wrong(None), payload, None, [], [], 0, ["SAT_MATH"], PARAMS, NOW
    )
    assert result.evidence[0].weight == pytest.approx(0.8 * 0.7)


def test_reconcile_partial_multi_select_direction_zero():
    inst = _instance(type="multi_select")
    payload = _payload(mode="topic")
    result = reconcile_task_answer(
        inst, _partial(0.5), payload, None, [], [], 0, ["SAT_MATH"], PARAMS, NOW
    )
    ev = result.evidence[0]
    assert ev.direction == 0
    assert ev.share == pytest.approx(0.5)


def test_reconcile_rule_root_when_prereq_weak():
    inst = _instance()
    payload = _payload(mode="topic")
    prereq = Prerequisite(skill_id="math.alg.linear_eq", strength=0.9, depth=1)
    prereq_state = _state(skill_id="math.alg.linear_eq").model_copy(
        update={"p_recall": 0.4, "confidence": 0.6}
    )
    result = reconcile_task_answer(
        inst,
        _wrong("lib.abs_single_branch"),
        payload,
        None,
        [(prereq, prereq_state)],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    assert len(result.root_causes) == 1
    assert result.root_causes[0].source == "rule"
    assert result.root_causes[0].root_skill_id == "math.alg.linear_eq"


def test_reconcile_is_pure():
    inst = _instance()
    payload = _payload(mode="topic")
    r1 = reconcile_task_answer(
        inst,
        _wrong("lib.abs_single_branch"),
        payload,
        None,
        [],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    r2 = reconcile_task_answer(
        inst,
        _wrong("lib.abs_single_branch"),
        payload,
        None,
        [],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    assert r1.model_dump() == r2.model_dump()


def test_reconcile_task_in_chat_is_weighted_like_a_task():
    """Ответ на задачу из чата — это разбор задачи (§4.3 «task_in_chat»),
    а не реплика: раньше пара (source="chat", mode="chat", kind=None)
    отсутствовала в таблице весов и свидетельство получало вес 0."""
    inst = _instance()
    result = reconcile_task_answer(
        inst,
        _correct(),
        _payload(mode="chat"),
        None,
        [],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    evidence = result.evidence[0]
    assert evidence.kind == "task_in_chat"
    assert evidence.weight == pytest.approx(0.8)
    assert evidence.tier == 2


def test_reconcile_evidence_carries_the_instance_it_came_from():
    """Без ctx.instance_id `explain_belief` не может показать задачу,
    на которой сложилось убеждение (§10.5)."""
    inst = _instance()
    result = reconcile_task_answer(
        inst,
        _correct(),
        _payload(),
        None,
        [],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    for evidence in result.evidence:
        assert evidence.context is not None
        assert evidence.context.instance_id == inst.id


def test_reconcile_words_follow_the_exam_target(monkeypatch):
    """p_target приходит из roadmap.requirements (цель сохранённых программ),
    а не берётся как верхняя граница params.p_target_max."""
    seen: list[float] = []

    def fake_words(state, p_target, params):
        seen.append(p_target)
        return "ok"

    monkeypatch.setattr("app.knowledge.reconcile.state_words", fake_words)
    args = (
        _instance(),
        _correct(),
        _payload(),
        _state(),
        [],
        [],
        0,
        ["SAT_MATH"],
        PARAMS,
        NOW,
    )
    reconcile_task_answer(*args)
    reconcile_task_answer(*args, p_target=0.62)
    assert seen == [PARAMS.p_target_max, 0.62]
