"""B1 profile update apply interface."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.events import Event


async def apply_profile_updated(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> None:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
