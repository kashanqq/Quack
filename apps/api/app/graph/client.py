"""Neo4j driver lifecycle — thin wrapper, no queries.

B3 connects this from app.main.lifespan:

    app.state.neo4j = await graph.client.create_driver(settings)
    ...
    await graph.client.close_driver(app.state.neo4j)

Source: 00-contracts.md §7 (точки стыка), 20-B1.md §2.1.
"""

from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import Settings


async def create_driver(settings: Settings) -> AsyncDriver:
    """Create an async Neo4j driver and verify connectivity.

    Uses NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD from Settings.
    Raises neo4j.exceptions.ServiceUnavailable if the database is unreachable.
    """
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
    )
    await driver.verify_connectivity()
    return driver


async def close_driver(driver: AsyncDriver) -> None:
    """Close the driver and release its connection pool."""
    await driver.close()