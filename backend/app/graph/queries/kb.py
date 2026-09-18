"""Read-only queries over the admission knowledge base (Neo4j).

Source: memory-architecture-quack.md §2.3, 20-B1.md §2.5.
Every result carries source, checked_at, is_demo.

All functions take an AsyncDriver as first arg.
"""

from __future__ import annotations

from neo4j import AsyncDriver

from app.graph import labels as L
from app.schemas.knowledge import AdmissionRouteOut, FactOut, TestDate


async def get_admission_route(
    driver: AsyncDriver, country_id: str
) -> list[AdmissionRouteOut]:
    """All routes for a country, each with requirements."""
    query = f"""
    MATCH (c:{L.COUNTRY} {{id: $country_id}})-[:{L.HAS_ROUTE}]->(r:{L.ADMISSION_ROUTE})
    OPTIONAL MATCH (r)-[:{L.REQUIRES}]->(req:{L.REQUIREMENT})
    WITH r, collect(DISTINCT {{
        type: req.type, exam_id: req.exam_id, threshold: req.threshold,
        comparator: req.comparator, description: req.description, source: req.source
    }}) AS requirements
    RETURN r.id AS id, r.name AS name, r.description AS description,
           r.source AS source, r.is_demo AS is_demo, requirements
    ORDER BY r.id
    """
    out: list[AdmissionRouteOut] = []
    async with driver.session() as session:
        result = await session.run(query, country_id=country_id)
        async for rec in result:
            reqs = [r for r in rec["requirements"] if r.get("type") is not None]
            out.append(
                AdmissionRouteOut(
                    id=rec["id"],
                    name=rec["name"],
                    description=rec["description"],
                    country_id=country_id,
                    requirements=reqs,
                    source=rec["source"],
                    is_demo=bool(rec["is_demo"]),
                )
            )
    return out


async def list_requirements(driver: AsyncDriver, program_id: str) -> list[dict]:
    """Program requirements — read from Postgres in the real path.

    Program nodes are not in Neo4j (they live in Postgres `programs_cache`).
    This function returns an empty list for now — placeholder until B3 wires
    programs into the graph or we route through Postgres.
    """
    return []


async def list_test_dates(driver: AsyncDriver, exam_id: str) -> list[TestDate]:
    """TestDate nodes attached to an Exam, ordered by date."""
    query = f"""
    MATCH (e:{L.EXAM} {{id: $exam_id}})-[:{L.HAS_DATE}]->(d:{L.TEST_DATE})
    RETURN d.date AS date, d.registration_deadline AS registration_deadline,
           d.late_deadline AS late_deadline, d.source AS source,
           d.checked_at AS checked_at, d.is_demo AS is_demo
    ORDER BY d.date
    """
    out: list[TestDate] = []
    async with driver.session() as session:
        result = await session.run(query, exam_id=exam_id)
        async for rec in result:
            out.append(
                TestDate(
                    exam_id=exam_id,
                    date=rec["date"],
                    registration_deadline=rec["registration_deadline"],
                    late_deadline=rec["late_deadline"],
                    source=rec["source"] or "",
                    checked_at=rec["checked_at"],
                    is_demo=bool(rec["is_demo"]),
                )
            )
    return out


async def list_facts_about(driver: AsyncDriver, node_id: str) -> list[FactOut]:
    """All Fact nodes attached to a given node_id (Exam or Country id)."""
    query = f"""
    MATCH (f:{L.FACT} {{node_id: $node_id}})
    RETURN f.text AS text, f.source AS source, f.checked_at AS checked_at,
           f.is_demo AS is_demo
    ORDER BY f.id
    """
    out: list[FactOut] = []
    async with driver.session() as session:
        result = await session.run(query, node_id=node_id)
        async for rec in result:
            out.append(
                FactOut(
                    text=rec["text"],
                    source=rec["source"],
                    checked_at=rec["checked_at"],
                    is_demo=bool(rec["is_demo"]),
                )
            )
    return out
