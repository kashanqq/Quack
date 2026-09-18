"""Integration tests over the canonical layer — 20-B1.md §7.

Require a live Neo4j with seed_skills + seed_exam_formats loaded.
The `graph` fixture skips if Neo4j is unreachable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from app.graph.queries.canonical import (
    get_exam_format,
    get_prerequisites,
    is_dag,
    list_exam_skills,
)
from app.graph.schema import apply_schema
from app.seed.exam_formats import seed_exam_formats
from app.seed.skills import seed_skills


pytestmark = [pytest.mark.phase1, pytest.mark.integration]


DATA = Path(__file__).resolve().parents[3] / "data"


@pytest_asyncio.fixture(scope="module")
async def seeded_graph(graph):
    """Seed skills + exam formats once for the module, then yield the driver."""
    await apply_schema(graph, 384)
    await seed_skills(graph, DATA / "skills")
    await seed_exam_formats(graph, DATA / "exam_formats")
    yield graph


async def test_list_exam_skills_not_empty(seeded_graph):
    skills = await list_exam_skills(seeded_graph, "SAT_MATH")
    assert len(skills) > 0


async def test_sat_weights_sum_to_max_raw_score(seeded_graph):
    skills = await list_exam_skills(seeded_graph, "SAT_MATH")
    total = sum(s.weight for s in skills)
    assert total == pytest.approx(44.0, abs=1e-6)


async def test_ent_weights_sum_to_max_raw_score(seeded_graph):
    skills = await list_exam_skills(seeded_graph, "ENT_MATH")
    total = sum(s.weight for s in skills)
    assert total == pytest.approx(50.0, abs=1e-6)


async def test_common_skill_has_two_has_skill_edges(seeded_graph):
    async with seeded_graph.session() as session:
        result = await session.run(
            """
            MATCH (a:Area)-[:HAS_SKILL]->(s:Skill {id: 'math.alg.linear_eq'})
            RETURN count(a) AS n
            """
        )
        rec = await result.single()
    assert rec["n"] >= 2


async def test_get_prerequisites_two_levels(seeded_graph):
    prereqs = await get_prerequisites(seeded_graph, "sat.adv.quadratic_functions", depth=2)
    assert len(prereqs) > 0
    depths = {p.depth for p in prereqs}
    assert 1 in depths


async def test_is_dag(seeded_graph):
    assert await is_dag(seeded_graph) is True


async def test_get_exam_format_ent(seeded_graph):
    fmt = await get_exam_format(seeded_graph, "ENT_MATH")
    assert fmt is not None
    assert fmt.exam_id == "ENT_MATH"
    assert len(fmt.sections) >= 1
    assert fmt.sections[0].n_items > 0
    assert isinstance(fmt.is_demo, bool)