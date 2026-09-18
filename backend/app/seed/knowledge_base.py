"""Load admission knowledge base — memory-architecture §2.3.

Reads two files:
  - data/knowledge_base/exams.json: array of Fact nodes with node_id (Exam id)
  - data/knowledge_base/routes.json: array of {country_id, routes: [...]}

Idempotent MERGE by id.

Source: 20-B1.md §6.2, §6.3.
"""

from __future__ import annotations

import json
from pathlib import Path

from neo4j import AsyncDriver
from pydantic import BaseModel, Field

from app.graph import labels as L
from app.seed.skills import SeedError, SeedReport


class FactIn(BaseModel):
    id: str
    node_id: str
    text: str
    source: str | None = None
    checked_at: str | None = None
    is_demo: bool = False


class RequirementIn(BaseModel):
    type: str
    exam_id: str | None = None
    threshold: float | list | None = None
    comparator: str
    description: str
    source: str | None = None


class RouteIn(BaseModel):
    id: str
    name: str
    description: str
    requirements: list[RequirementIn] = Field(default_factory=list)
    source: str | None = None
    checked_at: str | None = None
    is_demo: bool = False


class CountryRoutes(BaseModel):
    country_id: str
    routes: list[RouteIn]


async def seed_knowledge_base(driver: AsyncDriver, path: Path) -> SeedReport:
    """Load exams.json (Fact nodes) and routes.json (Country–Route–Requirement)."""
    report = SeedReport()
    exams_path = path / "exams.json"
    routes_path = path / "routes.json"

    if not exams_path.exists() and not routes_path.exists():
        raise SeedError(str(path), "no exams.json or routes.json")

    if exams_path.exists():
        report = report + await _seed_facts(driver, exams_path)
    if routes_path.exists():
        report = report + await _seed_routes(driver, routes_path)

    return report


async def _seed_facts(driver: AsyncDriver, path: Path) -> SeedReport:
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        entries = [FactIn.model_validate(r) for r in raw]
    except Exception as exc:  # noqa: BLE001
        raise SeedError(str(path), str(exc)) from exc

    report = SeedReport()
    async with driver.session() as session:
        for f in entries:
            await session.run(
                f"""
                MERGE (fact:{L.FACT} {{id: $id}})
                SET fact.node_id = $node_id,
                    fact.text = $text,
                    fact.source = $source,
                    fact.checked_at = $checked_at,
                    fact.is_demo = $is_demo
                """,
                id=f.id,
                node_id=f.node_id,
                text=f.text,
                source=f.source,
                checked_at=f.checked_at,
                is_demo=f.is_demo,
            )
            report.nodes += 1
    return report


async def _seed_routes(driver: AsyncDriver, path: Path) -> SeedReport:
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        countries = [CountryRoutes.model_validate(c) for c in raw]
    except Exception as exc:  # noqa: BLE001
        raise SeedError(str(path), str(exc)) from exc

    report = SeedReport()
    async with driver.session() as session:
        for country in countries:
            await session.run(
                f"""
                MERGE (c:{L.COUNTRY} {{id: $id}})
                """,
                id=country.country_id,
            )
            report.nodes += 1

            for route in country.routes:
                await session.run(
                    f"""
                    MATCH (c:{L.COUNTRY} {{id: $cid}})
                    MERGE (r:{L.ADMISSION_ROUTE} {{id: $rid}})
                    SET r.name = $name,
                        r.description = $description,
                        r.source = $source,
                        r.checked_at = $checked_at,
                        r.is_demo = $is_demo,
                        r.country_id = $cid
                    MERGE (c)-[:{L.HAS_ROUTE}]->(r)
                    """,
                    cid=country.country_id,
                    rid=route.id,
                    name=route.name,
                    description=route.description,
                    source=route.source,
                    checked_at=route.checked_at,
                    is_demo=route.is_demo,
                )
                report.nodes += 1
                report.rels += 1

                for i, req in enumerate(route.requirements):
                    await session.run(
                        f"""
                        MATCH (r:{L.ADMISSION_ROUTE} {{id: $rid}})
                        MERGE (req:{L.REQUIREMENT} {{route_id: $rid, idx: $idx}})
                        SET req.type = $type,
                            req.exam_id = $exam_id,
                            req.threshold = $threshold,
                            req.comparator = $comparator,
                            req.description = $description,
                            req.source = $source
                        MERGE (r)-[:{L.REQUIRES}]->(req)
                        """,
                        rid=route.id,
                        idx=i,
                        type=req.type,
                        exam_id=req.exam_id,
                        threshold=_threshold_to_float(req.threshold),
                        comparator=req.comparator,
                        description=req.description,
                        source=req.source,
                    )
                    report.nodes += 1
                    report.rels += 1
    return report


def _threshold_to_float(value) -> float | None:
    """Neo4j doesn't allow mixed types — return None for list thresholds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    # for ranges we'd need two values; keep None and description carries the details
    return None
