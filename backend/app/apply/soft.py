"""Soft match: the summary hash, the candidate list and the read side (§5).

The hash is over the *normalized* trait summary: fixing a comma must not
invalidate every judgement the model already made. Verbatim phrases are
deliberately outside the hash — they are already reflected in the summary,
and hashing them would recompute every program on every new phrase.
"""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import KnowledgeParams
from app.db.repo import programs as programs_repo
from app.db.repo import soft_matches as soft_repo
from app.events.dispatch import RuleDeps
from app.schemas.matching import SoftMatchOut
from app.schemas.programs import Program
from app.schemas.texts import ProgramBrief, SoftMatchInputs

_WHITESPACE = re.compile(r"\s+")
_MAX_SUMMARY_CHARS = 1500
_MAX_VERBATIM = 10
_MAX_VERBATIM_CHARS = 100


def normalize_summary(summary: str) -> str:
    return _WHITESPACE.sub(" ", (summary or "").strip()).casefold()


def summary_hash(summary: str) -> str:
    return hashlib.sha256(normalize_summary(summary).encode("utf-8")).hexdigest()


def build_inputs(profile, program: Program) -> SoftMatchInputs:
    return SoftMatchInputs(
        traits_summary=(profile.traits.summary or "")[:_MAX_SUMMARY_CHARS],
        traits_verbatim=[
            item[:_MAX_VERBATIM_CHARS]
            for item in (profile.traits.verbatim or [])[-_MAX_VERBATIM:]
        ],
        program=ProgramBrief(
            university=program.university,
            country=program.country,
            city=program.city,
            language=program.language,
            direction=program.direction,
            environment_text=program.environment_text,
            scholarships_note=program.scholarships_note,
        ),
    )


async def candidates(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    program_ids: list[str],
) -> list[Program]:
    """Top of the ranking plus everything saved, `impossible` last (§5.2)."""
    if program_ids:
        out: list[Program] = []
        for program_id in program_ids:
            program = await programs_repo.get_program(session, program_id)
            if program is not None and not program.flagged:
                out.append(program)
        return out

    from app.apply import matching as apply_matching

    params: KnowledgeParams = deps.params
    matching = await apply_matching.run_matching(
        session, deps, student_id, limit=params.soft_match_max_candidates
    )
    ordered: list[Program] = []
    postponed: list[Program] = []
    for item in matching.items[: params.soft_match_max_candidates]:
        if item.program.flagged:
            continue
        (postponed if item.realism == "impossible" else ordered).append(item.program)
    known = {program.id for program in [*ordered, *postponed]}
    for program in await programs_repo.list_saved_programs(session, student_id):
        if program.id not in known and not program.flagged:
            ordered.append(program)
    return [*ordered, *postponed]


async def read_scores(
    session: AsyncSession,
    student_id: UUID,
    summary: str,
    program_ids: list[str],
    prompt_version: str,
) -> tuple[dict[str, SoftMatchOut], str]:
    """(rows by program, summary hash) — empty summary means no soft factor."""
    del student_id
    normalized = normalize_summary(summary)
    if not normalized:
        return {}, ""
    digest = summary_hash(summary)
    rows = await soft_repo.get_many(session, digest, program_ids, prompt_version)
    return rows, digest
