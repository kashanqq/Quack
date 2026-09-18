"""Neo4j driver lifecycle — soft-fail wrapper.

B3 connects this from app.main.lifespan:

    driver = graph_client.create_driver(settings)
    if inspect.isawaitable(driver):
        driver = await driver
    ...
    await graph_client.close_driver(driver)

Contract (agreed with B3, aligned with product-logic §6.3):
  - create_driver returns AsyncDriver on success, or None if the graph is
    unreachable. It NEVER raises on connectivity failure — the API must
    keep serving requests that don't need Neo4j.
  - close_driver(None) is a no-op.

Source: 00-contracts.md §7, 20-B1.md §2.1.
"""

from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import Settings


async def create_driver(settings: Settings) -> AsyncDriver | None:
    """Create an async Neo4j driver and verify connectivity.

    Returns None if the database is unreachable — the caller (B3 lifespan)
    treats that as "graph layer unavailable" and keeps the app running.
    """
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
    )
    try:
        await driver.verify_connectivity()
    except Exception:  # noqa: BLE001 — soft-fail, log is B3's concern
        await driver.close()
        return None
    return driver


async def close_driver(driver: AsyncDriver | None) -> None:
    """Close the driver. No-op if driver is None (graph was unavailable)."""
    if driver is None:
        return
    await driver.close()