"""Event → graph reconciliation (phase 2).

Source: memory-architecture-quack.md §8.2, 20-B1.md §3.4.
The 11-step handler for task.answered. Registered via events.dispatch.on
in phase 2 — see 00-contracts.md §7.
"""

from __future__ import annotations

from app.events.store import Event


async def on_task_answered(session, event: Event) -> None:
    """Phase 2: apply task.answered (11 steps of §8.2).

    1. Write event → event_id (already done by store.append).
    2. Read the TaskInstance, grade the answer.
    3. Compute weight (tier, mode, seen_template, matched).
    4. Create Evidence with context.
    5. Update KnowledgeState (new node, PREVIOUS link).
    6. Update MisconceptionState (occurrence/strong/avoided).
    7. Recompute triggers.
    8. Root rule: prerequisite gap → ROOT_CAUSE.
    9. seen_templates += 1.
    10. Rebuild set queue and forecast.
    11. Return result, solution, new state, misconception change.
    """
    raise NotImplementedError("phase 2")
