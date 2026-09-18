"""Load the misconception library into Neo4j — memory-architecture §5.4.

Each library misconception gets an embedding from Embedder and connects to
its skills via ABOUT. Validates that every skill_id exists.

Source: 20-B1.md §6.3.
"""

from __future__ import annotations

import json
from pathlib import Path

from neo4j import AsyncDriver
from pydantic import BaseModel, Field

from app.embeddings import Embedder
from app.graph import labels as L
from app.seed.skills import SeedError, SeedReport


class MisconceptionFileEntry(BaseModel):
    id: str
    name: str
    description: str
    error_class: str
    skill_ids: list[str]
    exam_specific: str | None = None


async def seed_misconceptions(
    driver: AsyncDriver,
    path: Path,
    embedder: Embedder | None = None,
) -> SeedReport:
    """Load data/misconceptions/library.json into Neo4j."""
    if path.is_dir():
        path = path / "library.json"
    if embedder is None:
        from app.config import settings

        embedder = Embedder(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM)
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        entries = [MisconceptionFileEntry.model_validate(r) for r in raw]
    except Exception as exc:  # noqa: BLE001
        raise SeedError(str(path), str(exc)) from exc

    if not entries:
        raise SeedError(str(path), "library is empty")

    # check all skills exist
    async with driver.session() as session:
        for entry in entries:
            for sid in entry.skill_ids:
                rec = await (
                    await session.run(
                        f"MATCH (s:{L.SKILL} {{id: $id}}) RETURN s.id AS id", id=sid
                    )
                ).single()
                if rec is None:
                    raise SeedError(
                        str(path),
                        f"skill {sid} not found for misconception {entry.id}",
                    )

    # compute embeddings in one batch
    texts = [f"{e.name}. {e.description}" for e in entries]
    vectors = embedder.embed(texts)

    report = SeedReport()
    async with driver.session() as session:
        for entry, vec in zip(entries, vectors, strict=True):
            await session.run(
                f"""
                MERGE (m:{L.MISCONCEPTION} {{id: $id}})
                SET m.name = $name, m.description = $description,
                    m.error_class = $error_class,
                    m.exam_specific = $exam_specific,
                    m.scope = 'library',
                    m.embedding = $embedding
                """,
                id=entry.id,
                name=entry.name,
                description=entry.description,
                error_class=entry.error_class,
                exam_specific=entry.exam_specific,
                embedding=vec,
            )
            report.nodes += 1

            for sid in entry.skill_ids:
                await session.run(
                    f"""
                    MATCH (m:{L.MISCONCEPTION} {{id: $mid}})
                    MATCH (s:{L.SKILL} {{id: $sid}})
                    MERGE (m)-[:{L.ABOUT}]->(s)
                    """,
                    mid=entry.id,
                    sid=sid,
                )
                report.rels += 1

    return report
