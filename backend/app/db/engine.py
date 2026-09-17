"""Async PostgreSQL engine and session factories for API, seed and workers."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Create an engine; connections are opened only when first used."""
    return create_async_engine(settings.DATABASE_URL)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def close_engine(engine: AsyncEngine) -> None:
    """Dispose the pool after callers have closed their sessions/connections."""
    await engine.dispose()
