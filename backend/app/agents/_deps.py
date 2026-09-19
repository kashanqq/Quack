"""Rule dependencies for tool bodies — the same `RuleDeps` the routes build.

A tool that writes (`update_profile`, `save_program`, `get_task`) goes
through the very `events.store.append → dispatch → apply/*` path a route
does, so it needs the same `RuleDeps` (docs/tz/phase3-agents.md §3.3).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.config import settings
from app.events.dispatch import RuleDeps

if TYPE_CHECKING:
    from app.agents.router import AgentDeps


def rule_deps(deps: AgentDeps) -> RuleDeps:
    return RuleDeps(
        graph=deps.graph,
        redis=deps.redis,
        params=settings.knowledge,
        now=lambda: datetime.now(UTC),
    )
