"""Diagnostic repository names reserved by Phase 2 contract §7.4.

The contract names these functions but omits their parameter lists. Keep them
importable until the signatures are agreed; no persistence semantics are guessed.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def create_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("phase 2")


async def get_active_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("phase 2")


async def save_state(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("phase 2")


async def complete_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("phase 2")
