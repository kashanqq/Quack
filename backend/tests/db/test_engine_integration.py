"""Read-only PostgreSQL smoke test; set TEST_DATABASE_URL to opt in."""

import os

import pytest
from sqlalchemy import text

from app.config import Settings
from app.db.engine import close_engine, create_engine, create_sessionmaker


@pytest.mark.integration
async def test_select_one():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to an available PostgreSQL test database")

    engine = create_engine(Settings(ENV="local", DATABASE_URL=database_url))
    try:
        factory = create_sessionmaker(engine)
        async with factory() as session:
            assert await session.scalar(text("SELECT 1")) == 1
    finally:
        await close_engine(engine)
