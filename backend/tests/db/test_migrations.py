"""Phase 1 and Phase 2 schema and migration checks."""

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
PHASE2_TABLES = {
    "sets",
    "set_topics",
    "diagnostic_runs",
    "mock_runs",
    "milestone_marks",
    "forecast_cache",
}
# Фаза 4 (§1.7) — три новые таблицы, одна миграция `0003_phase4`.
PHASE4_TABLES = {
    "student_aggregates",
    "soft_matches",
    "job_outbox",
}
PHASE2_TASK_COLUMNS = {"mode", "issued_event_id", "answered_at", "correct"}
PHASE1_TASK_COLUMNS = {
    "id",
    "template_id",
    "seed",
    "exam_id",
    "type",
    "stem_rendered",
    "options",
    "answer",
    "trap_answers",
    "solution_rendered",
    "figure_url",
    "created_at",
    "student_id",
    "skill_id",
    "time_reference_sec",
    "difficulty",
    "tags",
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


def test_metadata_has_phase1_and_phase2_tables_and_constraints():
    assert set(Base.metadata.tables) == EXPECTED_TABLES | PHASE2_TABLES | PHASE4_TABLES
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
    assert set(Base.metadata.tables["task_instances"].c.keys()) == (
        PHASE1_TASK_COLUMNS | PHASE2_TASK_COLUMNS
    )
    assert [
        column.name for column in Base.metadata.tables["set_topics"].primary_key
    ] == ["set_id", "skill_id"]
    assert [
        column.name for column in Base.metadata.tables["forecast_cache"].primary_key
    ] == ["student_id", "exam_id"]
    active_index = next(
        index
        for index in Base.metadata.tables["diagnostic_runs"].indexes
        if index.name == "uq_diagnostic_runs_active_student_exam"
    )
    assert active_index.unique
    assert str(active_index.dialect_options["postgresql"]["where"]) == (
        "status = 'active'"
    )
    assert Base.metadata.tables["task_instances"].c.answered_at.type.timezone is True


def test_offline_upgrade_contains_every_table_and_partial_indexes():
    result = _alembic("upgrade", "head", "--sql")
    assert result.returncode == 0, result.stderr
    for table_name in EXPECTED_TABLES | PHASE2_TABLES:
        assert f"CREATE TABLE {table_name} " in result.stdout
    assert "CREATE INDEX ix_events_chat_unprocessed" in result.stdout
    assert (
        "ON events (chat_id, processed_at) WHERE processed_at IS NULL" in result.stdout
    )
    assert "CREATE UNIQUE INDEX uq_diagnostic_runs_active_student_exam" in result.stdout
    assert "WHERE status = 'active'" in result.stdout
    for column_name in PHASE2_TASK_COLUMNS:
        assert f"ADD COLUMN {column_name}" in result.stdout


def test_offline_downgrade_removes_only_phase2_schema():
    result = _alembic("downgrade", "0002_phase2:0001_init", "--sql")
    assert result.returncode == 0, result.stderr
    for table_name in PHASE2_TABLES:
        assert f"DROP TABLE {table_name}" in result.stdout
    for column_name in PHASE2_TASK_COLUMNS:
        assert f"DROP COLUMN {column_name}" in result.stdout
    for table_name in EXPECTED_TABLES:
        assert f"DROP TABLE {table_name}" not in result.stdout


async def _inspect_database(
    database_url: str,
) -> tuple[set[str], dict[str, str], set[str], dict[str, str]]:
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
                    {
                        column["name"]
                        for column in inspect(sync_connection).get_columns(
                            "task_instances"
                        )
                    }
                    if inspect(sync_connection).has_table("task_instances")
                    else set(),
                    {
                        row.name: row.definition
                        for row in sync_connection.exec_driver_sql(
                            "SELECT indexname AS name, indexdef AS definition "
                            "FROM pg_indexes WHERE schemaname = current_schema() "
                            "AND tablename = 'diagnostic_runs'"
                        )
                    },
                )
            )
    finally:
        await close_engine(engine)


@pytest.mark.integration
def test_phase2_upgrade_downgrade_and_reupgrade_on_empty_test_database():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to an empty quack_test PostgreSQL database")
    if make_url(database_url).database != "quack_test":
        pytest.fail("Migration integration test requires the quack_test database")

    # Alembic keeps its own bookkeeping table after `downgrade base`.
    tables_before, _, _, _ = asyncio.run(_inspect_database(database_url))
    if tables_before - {"alembic_version"}:
        pytest.skip("quack_test is not empty; refusing to alter existing tables")

    try:
        upgrade = _alembic("upgrade", "head", database_url=database_url)
        assert upgrade.returncode == 0, upgrade.stderr
        tables, indexes, task_columns, diagnostic_indexes = asyncio.run(
            _inspect_database(database_url)
        )
        assert EXPECTED_TABLES | PHASE2_TABLES <= tables
        assert task_columns == PHASE1_TASK_COLUMNS | PHASE2_TASK_COLUMNS
        assert "ix_events_chat_unprocessed" in indexes
        assert "WHERE (processed_at IS NULL)" in indexes["ix_events_chat_unprocessed"]
        assert "uq_diagnostic_runs_active_student_exam" in diagnostic_indexes
        assert (
            "UNIQUE INDEX"
            in diagnostic_indexes["uq_diagnostic_runs_active_student_exam"]
        )

        downgrade = _alembic("downgrade", "base", database_url=database_url)
        assert downgrade.returncode == 0, downgrade.stderr

        first = _alembic("upgrade", "0001_init", database_url=database_url)
        assert first.returncode == 0, first.stderr
        tables, _, task_columns, _ = asyncio.run(_inspect_database(database_url))
        assert tables - {"alembic_version"} == EXPECTED_TABLES
        assert task_columns == PHASE1_TASK_COLUMNS

        second = _alembic("upgrade", "0002_phase2", database_url=database_url)
        assert second.returncode == 0, second.stderr
        tables, _, task_columns, _ = asyncio.run(_inspect_database(database_url))
        assert tables - {"alembic_version"} == EXPECTED_TABLES | PHASE2_TABLES
        assert task_columns == PHASE1_TASK_COLUMNS | PHASE2_TASK_COLUMNS

        back_one = _alembic("downgrade", "-1", database_url=database_url)
        assert back_one.returncode == 0, back_one.stderr
        tables, _, task_columns, _ = asyncio.run(_inspect_database(database_url))
        assert tables - {"alembic_version"} == EXPECTED_TABLES
        assert task_columns == PHASE1_TASK_COLUMNS

        again = _alembic("upgrade", "head", database_url=database_url)
        assert again.returncode == 0, again.stderr
        tables, _, task_columns, _ = asyncio.run(_inspect_database(database_url))
        assert tables - {"alembic_version"} == EXPECTED_TABLES | PHASE2_TABLES
        assert task_columns == PHASE1_TASK_COLUMNS | PHASE2_TASK_COLUMNS
    finally:
        downgrade = _alembic("downgrade", "base", database_url=database_url)
        assert downgrade.returncode == 0, downgrade.stderr
    tables_after, _, _, _ = asyncio.run(_inspect_database(database_url))
    assert not tables_after - {"alembic_version"}
