"""Engine foundation tests without a running database."""

import runpy
from unittest.mock import AsyncMock, patch

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Settings
from app.db import engine as engine_module

TEST_URL = "postgresql+asyncpg://test:test@127.0.0.1:5432/quack_test"


def test_import_does_not_create_engine_or_connect():
    with (
        patch("sqlalchemy.ext.asyncio.create_async_engine") as create,
        patch("asyncpg.connect", new_callable=AsyncMock) as connect,
    ):
        runpy.run_path(engine_module.__file__)

    create.assert_not_called()
    connect.assert_not_called()


async def test_engine_uses_async_driver_without_connecting():
    config = Settings(ENV="local", DATABASE_URL=TEST_URL)
    with patch("asyncpg.connect", new_callable=AsyncMock) as connect:
        engine = engine_module.create_engine(config)
        try:
            assert isinstance(engine, AsyncEngine)
            assert engine.dialect.is_async
            assert engine.url.drivername == "postgresql+asyncpg"
            assert engine.url.render_as_string(hide_password=False) == TEST_URL
        finally:
            await engine_module.close_engine(engine)
        connect.assert_not_called()


async def test_sessionmaker_creates_independent_async_sessions():
    engine = engine_module.create_engine(Settings(ENV="local", DATABASE_URL=TEST_URL))
    try:
        factory = engine_module.create_sessionmaker(engine)
        assert isinstance(factory, async_sessionmaker)
        async with factory() as first, factory() as second:
            assert isinstance(first, AsyncSession)
            assert first is not second
            assert first.bind is engine
            assert second.bind is engine
            assert first.sync_session.expire_on_commit is False
    finally:
        await engine_module.close_engine(engine)


async def test_close_engine_disposes_pool():
    engine = engine_module.create_engine(Settings(ENV="local", DATABASE_URL=TEST_URL))
    disposed = []
    event.listen(engine.sync_engine, "engine_disposed", disposed.append)

    await engine_module.close_engine(engine)

    assert disposed == [engine.sync_engine]
