"""Fixtures for graph integration tests.

Requires a live Neo4j — the `graph` fixture skips if unreachable.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase

from app.config import settings


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def graph():
    """Yield an AsyncDriver connected to Neo4j, or skip.

    Graph tests are integration — skipped if the database is down.
    """
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
    )
    try:
        await driver.verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        await driver.close()
        pytest.skip(f"waiting: Neo4j unreachable ({exc})")
    try:
        yield driver
    finally:
        await driver.close()
