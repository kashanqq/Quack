"""Shared test fixtures for B3 and Phase 2 integration tests."""

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import fakeredis.aioredis
import pytest
from sqlalchemy.engine import make_url

from app.config import KnowledgeParams, Settings
from app.db.engine import close_engine, create_engine, create_sessionmaker
from app.events.dispatch import RuleDeps
from app.llm.fake import FakeLLMClient
from app.schemas.programs import Program
from app.schemas.tasks import TaskTemplateSpec

FIXTURE_DATA = Path(__file__).resolve().parent / "fixtures" / "data"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def fake_llm():
    return FakeLLMClient()


@pytest.fixture
def frozen_now() -> datetime:
    return datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


@pytest.fixture
def rule_deps(redis, frozen_now) -> RuleDeps:
    return RuleDeps(
        graph=None,
        redis=redis,
        params=KnowledgeParams(),
        now=lambda: frozen_now,
    )


@pytest.fixture
async def db_session():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for Phase 2 database fixtures")
    if make_url(database_url).database != "quack_test":
        pytest.fail("Phase 2 database fixtures require the quack_test database")
    engine = create_engine(Settings(ENV="local", DATABASE_URL=database_url))
    try:
        factory = create_sessionmaker(engine)
        async with factory() as session:
            try:
                yield session
            finally:
                await session.rollback()
    finally:
        await close_engine(engine)


async def wipe_graph(driver) -> None:
    """Очистить граф перед сидированием.

    Все интеграционные модули работают с одной и той же локальной базой, а
    сидируют разные наборы (`data/skills` и `tests/fixtures/data/skills`).
    Без очистки веса навыков одного набора попадали в проверки другого, и
    результат зависел от порядка запуска модулей.
    """
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


@pytest.fixture
async def seeded_graph():
    uri = os.environ.get("TEST_NEO4J_URI")
    password = os.environ.get("TEST_NEO4J_PASSWORD")
    if not uri or not password:
        pytest.skip("TEST_NEO4J_URI and TEST_NEO4J_PASSWORD are required")

    from app.graph.client import close_driver, create_driver
    from app.seed.misconceptions import seed_misconceptions
    from app.seed.skills import ensure_schema, seed_skills
    from app.seed.templates import seed_templates

    driver = await create_driver(
        Settings(
            NEO4J_URI=uri,
            NEO4J_USER=os.environ.get("TEST_NEO4J_USER", "neo4j"),
            NEO4J_PASSWORD=password,
        )
    )
    if driver is None:
        pytest.fail("TEST_NEO4J_URI is configured but Neo4j is unavailable")

    class TestEmbedder:
        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[1.0] + [0.0] * 383 for _ in texts]

    try:
        await wipe_graph(driver)
        await ensure_schema(driver, 384)
        await seed_skills(driver, FIXTURE_DATA / "skills")
        await seed_misconceptions(
            driver,
            FIXTURE_DATA / "misconceptions" / "library.json",
            embedder=TestEmbedder(),
        )
        await seed_templates(driver, FIXTURE_DATA / "templates")
        yield driver
    finally:
        await close_driver(driver)


@dataclass(frozen=True)
class StudentWithSaved:
    student_id: UUID
    programs: list[Program]


@pytest.fixture
async def student_with_saved(db_session) -> StudentWithSaved:
    from app.db.repo.programs import save_program
    from app.seed.programs import seed_programs_floor, validate_programs_floor

    path = PROJECT_ROOT / "data" / "programs_floor" / "programs.json"
    await seed_programs_floor(db_session, path)
    programs = validate_programs_floor(path)[:2]
    student_id = uuid4()
    for program in programs:
        await save_program(db_session, student_id, program.id)
    return StudentWithSaved(student_id=student_id, programs=programs)


@pytest.fixture
async def templates_db(db_session) -> list[TaskTemplateSpec]:
    from app.db.repo.tasks import upsert_template

    templates = [
        TaskTemplateSpec.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted((FIXTURE_DATA / "templates").glob("*.json"))
    ]
    for template in templates:
        await upsert_template(db_session, template)
    return templates


@pytest.fixture
def fake_apply(monkeypatch):
    """Replace one B1 apply function with a predictable async response."""

    def replace(path: str, response: Any) -> AsyncMock:
        if not path.startswith("app.apply."):
            raise ValueError("fake_apply only patches app.apply functions")
        module_name, function_name = path.rsplit(".", 1)
        from importlib import import_module

        module = import_module(module_name)
        if not hasattr(module, function_name):
            raise AttributeError(path)
        original = getattr(module, function_name)
        mock = AsyncMock(return_value=response)
        mock.__name__ = function_name
        monkeypatch.setattr(module, function_name, mock)
        from app.events import dispatch as dispatcher

        for event_type, handlers in list(dispatcher._handlers.items()):
            if original in handlers:
                monkeypatch.setitem(
                    dispatcher._handlers,
                    event_type,
                    [mock if handler is original else handler for handler in handlers],
                )
        return mock

    return replace
