"""Integration tests over the admission knowledge base — 20-B1.md §7."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from app.graph.queries.kb import get_admission_route, list_facts_about
from app.graph.schema import apply_schema
from app.seed.knowledge_base import seed_knowledge_base

pytestmark = [
    pytest.mark.phase1,
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="module"),  # module-scoped driver fixtures
]


DATA = Path(__file__).resolve().parents[3] / "data"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def seeded_kb(graph):
    await apply_schema(graph, 384)
    await seed_knowledge_base(graph, DATA / "knowledge_base")
    yield graph


async def test_get_admission_route_kz(seeded_kb):
    routes = await get_admission_route(seeded_kb, "KZ")
    assert len(routes) >= 1
    assert all(r.country_id == "KZ" for r in routes)


async def test_routes_carry_source_or_is_demo(seeded_kb):
    routes = await get_admission_route(seeded_kb, "KZ")
    for r in routes:
        assert r.source is not None or r.is_demo is True


async def test_list_facts_about_sat(seeded_kb):
    facts = await list_facts_about(seeded_kb, "SAT_MATH")
    assert len(facts) >= 1
    assert all(f.text for f in facts)
