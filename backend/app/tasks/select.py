"""Template selection for one skill — memory-architecture §10.2.

Pure function: pick a template from the pool based on what the student has
seen and how their last grades went.

Source: 20-B1-phase2.md §4.1.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.tasks import TaskTemplateSpec


def pick_template(
    templates: list[TaskTemplateSpec],
    seen: dict[str, int],
    last_grades: list[bool],
    with_trap: str | None,
    other_structure_than: str | None,
    rng: random.Random,
) -> TaskTemplateSpec | None:
    """Choose one template from the pool.

    Rules (§10.2):
      - prefer templates with n_seen == 0
      - difficulty: one step up from last correct, one step down after two
        consecutive incorrect; start at the median difficulty of the pool
      - with_trap: only templates whose TRAPS or distractors reference this
        misconception id
      - other_structure_than: exclude templates with the same stem skeleton
        (compare template_id without the suffix after the last '_')
      - pool exhausted → minimum n_seen (repeat with a different seed)

    Returns:
        TaskTemplateSpec, or None if the pool is empty after filters.
    """
    raise NotImplementedError("phase 2")
