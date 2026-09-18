"""Apply the Neo4j schema (indices, constraints) idempotently.

Called by seed_skills first (20-B1.md §6.3). Reads schema.cypher from the
same directory and substitutes $dim with settings.EMBEDDING_DIM.

All statements use IF NOT EXISTS — safe to call on every seed run.
"""

from __future__ import annotations

from pathlib import Path

from neo4j import AsyncDriver

_SCHEMA_PATH = Path(__file__).parent / "schema.cypher"


def _load_statements(dim: int) -> list[str]:
    """Read schema.cypher, split by ';', substitute $dim, drop comments/empties."""
    raw = _SCHEMA_PATH.read_text(encoding="utf-8")
    raw = raw.replace("$dim", str(int(dim)))
    statements: list[str] = []
    for chunk in raw.split(";"):
        lines = [ln for ln in chunk.splitlines() if not ln.strip().startswith("//")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    return statements


async def apply_schema(driver: AsyncDriver, dim: int) -> None:
    """Run all schema statements sequentially. Idempotent."""
    statements = _load_statements(dim)
    async with driver.session() as session:
        for stmt in statements:
            await session.run(stmt)