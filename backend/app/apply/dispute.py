"""B1 misconception dispute apply interface."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.dispatch import RuleDeps
from app.schemas.events import Event
from app.schemas.knowledge import MisconceptionStateOut


async def apply_dispute(
    session: AsyncSession, event: Event, deps: RuleDeps
) -> MisconceptionStateOut:
    """Contract: 00-contracts-phase2.md §7.2."""
    raise NotImplementedError("phase 2")
