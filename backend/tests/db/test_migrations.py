"""Phase 1 schema and migration checks."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import make_url

from app.config import Settings
from app.db.engine import close_engine, create_engine
from app.db.models import Base

API_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
    "users",
    "events",
    "profiles",
    "saved_programs",
    "programs_cache",
    "task_templates",
    "task_instances",
    "seen_templates",
    "generated_texts",
    "set_summaries",
    "messages",
    "recommendations",
    "daily_aggregates",
}


def _alembic(
    *args: str, database_url: str | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=API_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_metadata_has_all_phase1_tables_and_constraints():
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert [
        column.name for column in Base.metadata.tables["saved_programs"].primary_key
    ] == [
        "student_id",
        "program_id",
    ]
    assert [
        column.name for column in Base.metadata.tables["seen_templates"].primary_key
    ] == [
        "student_id",
        "template_id",
    ]
    assert isinstance(Base.metadata.tables["events"].c.payload.type, JSONB)
    assert Base.metadata.tables["events"].c.occurred_at.type.timezone is True
    index = next(
        index
        for index in Base.metadata.tables["events"].indexes
        if index.name == "ix_events_chat_unprocessed"
    )
    assert str(index.dialect_options["postgresql"]["where"]) == "processed_at IS NULL"


def test_offline_upgrade_contains_every_table_and_partial_index():
    result = _alembic("upgrade", "head", "--sql")
    assert result.returncode == 0, result.stderr
    for table_name in EXPECTED_TABLES:
        assert f"CREATE TABLE {table_name} " in result.stdout
    assert "CREATE INDEX ix_events_chat_unprocessed" in result.stdout
    assert (
        "ON events (chat_id, processed_at) WHERE processed_at IS NULL" in result.stdout
    )


async def _inspect_database(database_url: str) -> tuple[set[str], dict[str, str]]:
    engine = create_engine(Settings(ENV="local", DATABASE_URL=database_url))
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: (
                    set(inspect(sync_connection).get_table_names()),
                    {
                        row.name: row.definition
                        for row in sync_connection.exec_driver_sql(
                            "SELECT indexname AS name, indexdef AS definition "
                            "FROM pg_indexes WHERE schemaname = current_schema() "
                            "AND tablename = 'events'"
                        )
                    },
                )
            )
    finally:
        await close_engine(engine)


@pytest.mark.integration
def test_upgrade_and_downgrade_on_empty_test_database():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to an empty quack_test PostgreSQL database")
    if make_url(database_url).database != "quack_test":
        pytest.fail("Migration integration test requires the quack_test database")

    # Alembic keeps its own bookkeeping table after `downgrade base`.
    tables_before, _ = asyncio.run(_inspect_database(database_url))
    if tables_before - {"alembic_version"}:
        pytest.skip("quack_test is not empty; refusing to alter existing tables")

    upgrade = _alembic("upgrade", "head", database_url=database_url)
    assert upgrade.returncode == 0, upgrade.stderr
    try:
        tables, indexes = asyncio.run(_inspect_database(database_url))
        assert EXPECTED_TABLES <= tables
        assert "ix_events_chat_unprocessed" in indexes
        assert "WHERE (processed_at IS NULL)" in indexes["ix_events_chat_unprocessed"]
    finally:
        downgrade = _alembic("downgrade", "base", database_url=database_url)
        assert downgrade.returncode == 0, downgrade.stderr
    tables_after, _ = asyncio.run(_inspect_database(database_url))
    assert not tables_after - {"alembic_version"}
