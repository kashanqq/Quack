"""Assemble the roadmap of sets from a queue — memory-architecture §10.1.

Pure function: cut the queue into sets, set deadlines, mark checks and the
final consolidation set. Respects a manually chosen `current` set.

Source: 20-B1-phase2.md §3.2, 00-contracts-phase2.md §7.1.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from app.config import KnowledgeParams
from app.schemas.knowledge import MisconceptionStateOut
from app.schemas.sets import SetOut
from app.sets.queue import QueueItem

_DAYS_PER_WEEK = 7
_DEFAULT_EFFORT_H = 4.0


class SetPlan(BaseModel):
    """One set in the roadmap — a plan to be persisted by repo.sets.replace_plan."""

    kind: Literal["regular", "review", "consolidation"]
    skill_ids: list[str]
    checks: list[str] = Field(default_factory=list)
    reviews: list[str] = Field(default_factory=list)
    deadline: date
    reason: str


def assemble_sets(
    queue: list[QueueItem],
    effort: dict[str, float],
    hours_per_week: int,
    next_test_date: date | None,
    misc_states: list[MisconceptionStateOut],
    current: SetOut | None,
    done_skill_ids: set[str],
    params: KnowledgeParams,
    today: date,
) -> list[SetPlan]:
    """Cut the queue into sets and give each a deadline.

    - set_size topics per set; checks не считаются топиками
    - deadline_i = deadline_{i-1} + ceil(Σ gap·effort_h / hours_per_week · 7)
      дней, не позже next_test_date − consolidation_days
    - последний сет перед тестом — consolidation без новых навыков
    - current не пересобирается: его skill_ids исключаются из очереди
    - reason — одна фраза про первый топик сета
    """
    if not queue and next_test_date is None:
        return []

    excluded: set[str] = set(done_skill_ids)
    if current is not None:
        excluded |= {t.skill_id for t in current.topics}

    filtered = [q for q in queue if q.skill_id not in excluded]
    checks = [q.skill_id for q in filtered if q.is_check]
    topics = [q for q in filtered if not q.is_check]

    limit: date | None = None
    if next_test_date is not None:
        limit = next_test_date - timedelta(days=params.consolidation_days)

    plans: list[SetPlan] = []
    deadline = today
    size = max(1, params.set_size)

    for idx in range(0, len(topics), size):
        chunk = topics[idx : idx + size]
        hours = sum(q.gap * effort.get(q.skill_id, _DEFAULT_EFFORT_H) for q in chunk)
        if hours_per_week > 0:
            days = math.ceil(hours / hours_per_week * _DAYS_PER_WEEK)
        else:
            days = 0
        deadline = deadline + timedelta(days=days)
        if limit is not None and deadline > limit:
            deadline = limit

        plans.append(
            SetPlan(
                kind="regular",
                skill_ids=[q.skill_id for q in chunk],
                checks=checks if idx == 0 else [],
                reviews=[],
                deadline=deadline,
                reason=_reason(chunk),
            )
        )

    if next_test_date is not None:
        consolidation_deadline = next_test_date - timedelta(days=1)
        if consolidation_deadline < today:
            consolidation_deadline = today
        plans.append(
            SetPlan(
                kind="consolidation",
                skill_ids=[],
                checks=[],
                reviews=[],
                deadline=consolidation_deadline,
                reason="закрепление перед тестом",
            )
        )

    if not plans and next_test_date is not None:
        plans.append(
            SetPlan(
                kind="review",
                skill_ids=[],
                checks=[],
                reviews=[],
                deadline=next_test_date - timedelta(days=1),
                reason="повторение всех закрытых навыков",
            )
        )

    return plans


def _reason(chunk: list[QueueItem]) -> str:
    if not chunk:
        return ""
    first = chunk[0]
    if first.is_root:
        return f"{first.skill_id}: корень недавних ошибок"
    return f"{first.skill_id}: наибольшая потребность"
