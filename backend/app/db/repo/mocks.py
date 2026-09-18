"""Mock repository names reserved by Phase 2 contract §7.4."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


async def create_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    """Signature pending: the Phase 2 contract lists no parameters."""
    raise NotImplementedError("phase 2")


async def get_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    """Signature pending: the Phase 2 contract lists no parameters."""
    raise NotImplementedError("phase 2")


async def save_progress(
    session: AsyncSession, run_id: UUID, answered_instance_ids: list[UUID]
) -> None:
    """Persist answered instance IDs once ownership is specified."""
    raise NotImplementedError("phase 2")


async def complete_run(
    session: AsyncSession, run_id: UUID, raw: float, scaled: float | None
) -> None:
    """Complete a mock run once ownership is specified."""
    raise NotImplementedError("phase 2")
