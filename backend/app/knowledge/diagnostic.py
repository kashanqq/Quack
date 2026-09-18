"""Diagnostic — adaptive descent by prerequisites — memory-architecture §8.4.

Pure state machine, no I/O. Takes a skill map, prerequisites, budget and a
sequence of grades; returns the next skill to ask and the final result.

Source: 20-B1-phase2.md §2.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.config import KnowledgeParams
from app.schemas.knowledge import (
    AreaOut,
    KnowledgeStateOut,
    Prerequisite,
    SkillWeight,
)

if TYPE_CHECKING:
    # B3's phase-2 skeleton models. Forward-refs until the skeleton is merged.
    from app.schemas.knowledge import RootCauseOut
    from app.schemas.tasks import Grade


# --- result types (owner: B1, declared here until B3's schemas land) ---


@dataclass
class DiagnosticState:
    """State of one diagnostic run — persisted as JSONB by repo.diagnostic."""

    exam_id: str
    budget_left: int
    reserve_left: int
    asked: list[str] = field(default_factory=list)
    answered: int = 0
    pending_descent: list[str] = field(default_factory=list)
    reask_queue: list[tuple[str, int]] = field(default_factory=list)
    roots_found: list[RootCauseOut] = field(default_factory=list)
    trap_hits: list[str] = field(default_factory=list)
    firm: list[str] = field(default_factory=list)
    shaky: list[str] = field(default_factory=list)
    last_grade_correct: bool | None = None


@dataclass
class DiagnosticResult:
    firm: list[str]
    shaky: list[str]
    roots: list[RootCauseOut]
    suspected: list[str]
    start_from: list[str]
    words: str


def start(
    exam_skills: list[SkillWeight],
    areas: list[AreaOut],
    prerequisites: list[Prerequisite],
    known_roots: list[RootCauseOut],
    budget: int | None,
    params: KnowledgeParams,
) -> DiagnosticState:
    """Build the initial state: budget by area share, roots first in pending_descent.

    budget = params.diag_base or the caller's n_tasks; reserve = params.diag_reserve.
    """
    raise NotImplementedError("phase 2")


def next_skill(
    state: DiagnosticState,
    prerequisites: list[Prerequisite],
    params: KnowledgeParams,
) -> str | None:
    """Return the next skill to ask, or None if the run is done.

    Priority: reask_queue pair with count == 0 → pending_descent → next by budget.
    """
    raise NotImplementedError("phase 2")


def apply_answer(
    state: DiagnosticState,
    skill_id: str,
    grade: Grade,
    prerequisites: list[Prerequisite],
    params: KnowledgeParams,
) -> DiagnosticState:
    """Advance the state after one answer.

    - correct → firm; prerequisites get indirect evidence (returned via state)
    - incorrect → shaky; if reserve_left > 0, push the strongest prerequisite
      into pending_descent (roots first)
    - trap hit → reask_queue.append((skill, diag_reask_after)); tick others
    """
    raise NotImplementedError("phase 2")


def finish(
    state: DiagnosticState,
    states: dict[str, KnowledgeStateOut],
    params: KnowledgeParams,
) -> DiagnosticResult:
    """Final result: firm / shaky / roots / suspected / start_from + words."""
    raise NotImplementedError("phase 2")
