"""Alembic environment using the application async PostgreSQL settings."""

import asyncio
import sys
from pathlib import Path

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.engine import close_engine, create_engine
from app.db.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(
                lambda sync_connection: context.configure(
                    connection=sync_connection,
                    target_metadata=target_metadata,
                )
            )
            await connection.run_sync(
                lambda sync_connection: run_migrations_in_transaction()
            )
    finally:
        await close_engine(engine)


def run_migrations_in_transaction() -> None:
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
