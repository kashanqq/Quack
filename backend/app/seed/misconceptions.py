"""Load the misconception library into Neo4j — memory-architecture §5.4.

Phase 2: reads the whole catalog data/misconceptions/*.json — one file per
area (alg, adv, psda, geo, ent_*). Merges entries, checks unique ids across
files, validates skill_ids against the graph. Each entry gets an embedding
and connects to its skills via ABOUT.

Source: 20-B1.md §6.3, 20-B1-phase2.md §0.1 п.2.
"""

from __future__ import annotations

import json
from pathlib import Path

from neo4j import AsyncDriver
from pydantic import BaseModel

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


def _load_catalog(
    path: Path,
) -> tuple[list[MisconceptionFileEntry], dict[str, list[str]]]:
    """Read all .json files under path. Return (entries, per_file_ids).

    Raises SeedError on parse errors, duplicate ids, or empty catalog.
    """
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = sorted(p for p in path.glob("*.json"))
    else:
        raise SeedError(str(path), "path does not exist")
    if not files:
        raise SeedError(str(path), "no misconception files found")

    entries: list[MisconceptionFileEntry] = []
    per_file: dict[str, list[str]] = {}
    for f in files:
        raw = json.loads(f.read_text(encoding="utf-8"))
        try:
            file_entries = [MisconceptionFileEntry.model_validate(r) for r in raw]
        except Exception as exc:  # noqa: BLE001
            raise SeedError(str(f), str(exc)) from exc
        per_file[f.name] = [e.id for e in file_entries]
        entries.extend(file_entries)

    if not entries:
        raise SeedError(str(path), "catalog is empty")

    # unique id across all files
    seen: dict[str, str] = {}
    for fname, ids in per_file.items():
        for mid in ids:
            if mid in seen:
                raise SeedError(
                    str(path),
                    f"duplicate misconception id {mid!r} in {fname} "
                    f"(also in {seen[mid]})",
                )
            seen[mid] = fname

    return entries, per_file


async def seed_misconceptions(
    driver: AsyncDriver,
    path: Path,
    embedder: Embedder | None = None,
) -> SeedReport:
    """Load data/misconceptions/*.json into Neo4j.

    path may be a directory (all *.json merged) or a single file.
    """
    entries, per_file = _load_catalog(path)

    if embedder is None:
        from app.config import settings

        embedder = Embedder(settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM)

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

    # per-file summary
    for fname, ids in per_file.items():
        print(f"  {fname}: {len(ids)} entries")

    return report
