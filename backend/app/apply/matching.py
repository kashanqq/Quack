"""Matching and comparison for the route and the assistant's tools.

Ownership exception (docs/tz/phase3-agents.md §5.2 F13, §9 item 14): this is a
B3 file inside the B1 `apply/` package. `GET /matching` and the selection
tool `run_matching` must return the same numbers and the same order (жюри,
step 4) — so both call this one implementation instead of each assembling
the inputs itself. The rules stay in B1's pure `matching/*`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repo import forecast as forecast_repo
from app.db.repo import profiles as profile_repo
from app.db.repo import programs as program_repo
from app.errors import NotFound, ValidationFailed
from app.events.dispatch import RuleDeps
from app.graph.queries import kb
from app.matching import compare as compare_rules
from app.matching import hard, rank, realism
from app.schemas.common import ExamId
from app.schemas.knowledge import ForecastOut, TestDate
from app.schemas.matching import CompareOut, MatchingOut, MatchOut
from app.schemas.profile import Profile
from app.schemas.programs import Program


async def _inputs(
    session: AsyncSession, deps: RuleDeps, student_id: UUID
) -> tuple[
    Profile, list[Program], dict[ExamId, ForecastOut], dict[ExamId, list[TestDate]]
]:
    profile = await profile_repo.get_profile(session, student_id)
    programs = await program_repo.list_all(session)
    saved = await program_repo.list_saved_programs(session, student_id)
    exam_ids: set[ExamId] = {
        requirement.exam_id
        for program in saved
        for requirement in program.requirements
        if requirement.exam_id is not None
    }
    forecasts = {
        exam_id: forecast
        for exam_id in exam_ids
        if (forecast := await forecast_repo.get(session, student_id, exam_id))
        is not None
    }
    all_exam_ids: set[ExamId] = {
        requirement.exam_id
        for program in programs
        for requirement in program.requirements
        if requirement.exam_id is not None
    }
    # Граф недоступен — подборка без фактора сроков (тест-дат нет).
    test_dates = (
        {
            exam_id: await kb.list_test_dates(deps.graph, exam_id)
            for exam_id in all_exam_ids
        }
        if deps.graph is not None
        else {}
    )
    return profile, programs, forecasts, test_dates


async def run_matching(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, limit: int
) -> MatchingOut:
    """Hard filter → realism → rank; at least `min_candidates` items."""
    profile, programs, forecasts, test_dates = await _inputs(session, deps, student_id)
    hard_results = hard.hard_filter(
        profile, programs, forecasts, test_dates, deps.now().date(), deps.params
    )
    levels = {
        item.program_id: realism.realism(item, deps.params) for item in hard_results
    }
    ranked = rank.rank(profile, hard_results, soft_scores={}, params=deps.params)
    by_program = {program.id: program for program in programs}
    by_hard = {item.program_id: item for item in hard_results}
    items = [
        MatchOut(
            program=by_program[item.program_id],
            realism=levels[item.program_id],
            factors=by_hard[item.program_id].factors,
            assumptions=by_hard[item.program_id].assumptions,
            score=item.score,
            fits_text=None,
            soft_pending=True,
        )
        for item in ranked
    ]
    return MatchingOut(
        items=items[: max(limit, deps.params.min_candidates)],
        total=len(items),
        profile_readiness=profile.readiness,
        forecast_used=bool(forecasts),
        empty_reason=hard.explain_empty(hard_results) if not hard_results else None,
    )


async def compare_programs(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, program_ids: list[str]
) -> CompareOut:
    """Side-by-side comparison of 2–4 distinct, unflagged programs."""
    if (
        not 2 <= len(program_ids) <= 4
        or len(set(program_ids)) != len(program_ids)
        or not all(program_ids)
    ):
        raise ValidationFailed("select 2 to 4 distinct programs")
    profile = await profile_repo.get_profile(session, student_id)
    programs = []
    for program_id in program_ids:
        program = await program_repo.get_program(session, program_id)
        if program is None or program.flagged:
            raise NotFound("program not found")
        programs.append(program)
    hard_results = hard.hard_filter(
        profile, programs, {}, {}, deps.now().date(), deps.params
    )
    result = compare_rules.compare(profile, programs, hard_results)
    return CompareOut.model_validate(
        {**result.model_dump(), "program_ids": program_ids, "conclusion": None}
    )
