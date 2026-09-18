"""Realism levels — product-logic §3.3, 20-B1-phase2.md §5.2.

Pure function: three words from academic and financial factor statuses.
No percentages leak to the student.

Source: 00-contracts-phase2.md §7.1.
"""

from __future__ import annotations

from app.config import KnowledgeParams
from app.matching.hard import HardResult
from app.schemas.common import Realism


def realism(hard: HardResult, params: KnowledgeParams) -> Realism:
    """Aggregate hard factors into one of three word-level labels.

    - grant_required (only_grant без стипендии) → impossible
    - любой hard-фактор `below` → try
    - все in_range / above → possible
    - unknown не штрафует

    Note: разрыв >15 % из §5.2 здесь не считается — у HardResult только
    статусы, без magnitudes. Если понадобится точнее — расширим HardResult.
    """
    if hard.grant_required:
        return "impossible"

    any_below = any(status == "below" for status in hard.realism_inputs.values())
    return "try" if any_below else "possible"
