"""HLR formulas from memory-architecture-quack.md §4.1–4.2.

All numbers come from 20-B1.md §7.1 and §12 config.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.config import KnowledgeParams
from app.knowledge.hlr import (
    apply_evidence,
    confidence,
    difficulty_factor,
    due_at,
    recall_p,
    spread_factor,
    updated_half_life,
    updated_p_at_obs,
)
from app.schemas.knowledge import EvidenceIn, KnowledgeStateOut


pytestmark = pytest.mark.phase1


# --- recall_p ---


def test_recall_p_24h_halflife_24h_is_half():
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    assert recall_p(24.0, t0, t0 + timedelta(hours=24)) == pytest.approx(0.5, abs=1e-9)


def test_recall_p_no_elapsed_is_one():
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    assert recall_p(24.0, t0, t0) == pytest.approx(1.0, abs=1e-9)


def test_recall_p_negative_elapsed_is_one():
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    assert recall_p(24.0, t0, t0 - timedelta(hours=1)) == pytest.approx(1.0, abs=1e-9)


def test_recall_p_48h_halflife_24h_is_quarter():
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    assert recall_p(24.0, t0, t0 + timedelta(hours=48)) == pytest.approx(0.25, abs=1e-9)


# --- difficulty_factor ---


def test_difficulty_factor_bounds():
    assert difficulty_factor(1) == pytest.approx(0.7, abs=1e-9)
    assert difficulty_factor(3) == pytest.approx(1.0, abs=1e-9)
    assert difficulty_factor(5) == pytest.approx(1.3, abs=1e-9)


# --- updated_half_life ---


def test_updated_half_life_correct_doubles_with_alpha_1():
    params = KnowledgeParams(alpha=1.0)
    h = updated_half_life(24.0, direction=1, weight=1.0, difficulty_factor=1.0, share=None, params=params)
    assert h == pytest.approx(48.0, abs=1e-9)


def test_updated_half_life_incorrect_halves_with_beta_half():
    params = KnowledgeParams(beta=0.5)
    h = updated_half_life(24.0, direction=-1, weight=1.0, difficulty_factor=1.0, share=None, params=params)
    assert h == pytest.approx(12.0, abs=1e-9)


def test_updated_half_life_incorrect_floor_at_quarter_of_h():
    # Проверяем floor 0.25 отдельно, h_min выставлен ниже, чтобы не мешал
    params = KnowledgeParams(beta=2.0, h_min=1.0)
    h = updated_half_life(24.0, direction=-1, weight=1.0, difficulty_factor=1.0, share=None, params=params)
    assert h == pytest.approx(6.0, abs=1e-9)  # 24 * max(0.25, 1 - 2) = 24 * 0.25


def test_updated_half_life_clamped_to_h_min():
    # 24 * 0.25 = 6 < h_min=12, значит клампится в 12
    params = KnowledgeParams(beta=2.0, h_min=12.0)
    h = updated_half_life(24.0, direction=-1, weight=1.0, difficulty_factor=1.0, share=None, params=params)
    assert h == pytest.approx(12.0, abs=1e-9)

# --- updated_p_at_obs ---


def test_updated_p_at_obs_correct():
    assert updated_p_at_obs(0.5, direction=1, weight=1.0, share=None) == pytest.approx(0.75, abs=1e-9)


def test_updated_p_at_obs_incorrect():
    assert updated_p_at_obs(0.5, direction=-1, weight=1.0, share=None) == pytest.approx(0.25, abs=1e-9)


def test_updated_p_at_obs_partial_between():
    params = KnowledgeParams()
    # partial = correct с weight*share, затем incorrect с weight*(1-share)
    p_after_correct = updated_p_at_obs(0.5, direction=1, weight=0.5, share=None)
    final = updated_p_at_obs(p_after_correct, direction=-1, weight=0.5, share=None)
    # Находится между чистым incorrect и чистым correct
    p_pure_correct = updated_p_at_obs(0.5, direction=1, weight=1.0, share=None)
    p_pure_incorrect = updated_p_at_obs(0.5, direction=-1, weight=1.0, share=None)
    assert p_pure_incorrect < final < p_pure_correct


# --- confidence ---


def test_confidence_zero_mass_is_zero():
    assert confidence(0.0, spread=1.0) == pytest.approx(0.0, abs=1e-9)


def test_confidence_monotonic_in_mass():
    c1 = confidence(1.0, spread=1.0)
    c2 = confidence(3.0, spread=1.0)
    c3 = confidence(10.0, spread=1.0)
    assert c1 < c2 < c3


def test_confidence_three_over_k_is_about_0632():
    # 1 - exp(-1) ≈ 0.632
    params = KnowledgeParams(k_confidence=3.0)
    c = confidence(3.0, spread=1.0)
    assert c == pytest.approx(0.632, abs=0.01)


def test_confidence_alternation_reduces():
    c_agree = confidence(3.0, spread=1.0)
    c_alt = confidence(3.0, spread=1.5)
    assert c_alt < c_agree


# --- spread_factor ---


def test_spread_factor_all_agree_is_one():
    assert spread_factor([1, 1, 1]) == pytest.approx(1.0)


def test_spread_factor_alternating_is_max():
    assert spread_factor([1, -1, 1, -1]) == pytest.approx(1.5)


def test_spread_factor_empty_is_one():
    assert spread_factor([]) == pytest.approx(1.0)


# --- due_at ---


def test_due_at_at_half_target():
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    due = due_at(t0, half_life_h=24.0, p_target=0.5)
    assert due == t0 + timedelta(hours=24)


def test_due_at_quarter_target():
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    due = due_at(t0, half_life_h=24.0, p_target=0.25)
    assert due == t0 + timedelta(hours=48)


# --- apply_evidence ---


def test_apply_evidence_none_state_creates_starting_state():
    params = KnowledgeParams(alpha=1.0, h0=24.0)
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    ev = _make_evidence(t0, tier=1, weight=1.0, direction=1)
    new_state = apply_evidence(None, ev, params=params)
    assert new_state.half_life_h == pytest.approx(24.0 * (1 + params.alpha))
    assert new_state.has_strong is True
    assert new_state.n_correct == 1
    assert new_state.evidence_mass == pytest.approx(1.0)


def test_apply_evidence_chat_tier_3_capped_at_p_chat_cap():
    params = KnowledgeParams(p_chat_cap=0.8)
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    state = _starting_state(t0)
    ev = _make_evidence(t0 + timedelta(hours=1), tier=3, weight=0.6, direction=1)
    new_state = apply_evidence(state, ev, params=params)
    assert new_state.p_at_obs <= params.p_chat_cap + 1e-9


def test_apply_evidence_tier_3_does_not_set_has_strong():
    params = KnowledgeParams()
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    state = _starting_state(t0)
    ev = _make_evidence(t0 + timedelta(hours=1), tier=3, weight=0.6, direction=1)
    new_state = apply_evidence(state, ev, params=params)
    assert new_state.has_strong is False


def test_apply_evidence_tier_2_sets_has_strong():
    params = KnowledgeParams()
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    state = _starting_state(t0)
    ev = _make_evidence(t0 + timedelta(hours=1), tier=2, weight=0.8, direction=1)
    new_state = apply_evidence(state, ev, params=params)
    assert new_state.has_strong is True


def test_apply_evidence_partial_halfway_between_correct_and_incorrect():
    params = KnowledgeParams()
    t0 = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    state = _starting_state(t0)

    ev_correct = _make_evidence(t0 + timedelta(hours=1), tier=2, weight=0.8, direction=1)
    state_correct = apply_evidence(state, ev_correct, params=params)

    state_incorrect = apply_evidence(state, _make_evidence(t0 + timedelta(hours=1), tier=2, weight=0.8, direction=-1), params=params)

    ev_partial = _make_evidence(t0 + timedelta(hours=1), tier=2, weight=0.8, direction=0, share=0.5)
    state_partial = apply_evidence(state, ev_partial, params=params)

    assert state_incorrect.half_life_h < state_partial.half_life_h < state_correct.half_life_h


# --- helpers ---


def _starting_state(t0: datetime) -> KnowledgeStateOut:
    return KnowledgeStateOut(
        skill_id="sat.alg.linear_eq",
        exam_id="SAT_MATH",
        p_recall=0.5,
        p_at_obs=0.5,
        half_life_h=24.0,
        confidence=0.0,
        evidence_mass=0.0,
        n_correct=0,
        n_incorrect=0,
        n_partial=0,
        has_strong=False,
        last_observed_at=t0,
        created_at=t0,
    )


def _make_evidence(
    observed_at: datetime,
    *,
    tier: int,
    weight: float,
    direction: int,
    share: float | None = None,
) -> EvidenceIn:
    return EvidenceIn(
        event_id=1,
        skill_id="sat.alg.linear_eq",
        exam_id="SAT_MATH",
        kind="task",
        tier=tier,  # type: ignore[arg-type]
        source="task",
        weight=weight,
        direction=direction,  # type: ignore[arg-type]
        share=share,
        difficulty_factor=1.0,
        summary=None,
        context=None,  # type: ignore[arg-type]
        observed_at=observed_at,
        extractor_version=None,
    )