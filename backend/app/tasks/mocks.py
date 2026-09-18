"""Mock assembly and scoring — memory-architecture §8.3, §10.2.

Pure functions: assemble a mock from templates, score a finished mock by the
rules of its exam section.

Source: 20-B1-phase2.md §4.2.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal

from app.config import KnowledgeParams

if TYPE_CHECKING:
    # B3's phase-2 skeleton: these live in schemas/tasks.py and schemas/mocks.py.
    from app.schemas.knowledge import ExamFormat, Section
    from app.schemas.tasks import Grade, TaskTemplateSpec

MockKind = Literal["mock_set", "mock_topic", "mock_misconception"]


def assemble_mock(
    kind: MockKind,
    section: Section,
    templates_by_skill: dict[str, list[TaskTemplateSpec]],
    seen: dict[str, int],
    rng: random.Random,
    params: KnowledgeParams,
) -> list[tuple[str, TaskTemplateSpec]]:
    """Pick templates for a mock of one kind.

    - mock_set: skills of one set, n ∈ [mock_set_min, mock_set_max],
      item_types and difficulty_shares proportional to the section
    - mock_topic: one skill, n ∈ [mock_topic_min, mock_topic_max]
    - mock_misconception: mock_misc_n templates with TRAPS on the misconception,
      across different skills if possible

    Returns:
        list of (skill_id, TaskTemplateSpec) — one per task, in order.
    """
    raise NotImplementedError("phase 2")


def score(
    section: Section,
    grades: list[Grade],
    exam_format: ExamFormat,
) -> tuple[float, float | None]:
    """Score a finished mock by the section's scoring_rule.

    Returns:
        (raw_score, scaled_score or None) — scaled uses the exam's ScaleTable.
    """
    raise NotImplementedError("phase 2")
