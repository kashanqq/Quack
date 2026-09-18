"""Seed CLI validation and idempotent B3 loaders."""

import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from app.seed import calendars, programs, users

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "seed.py"
DATA = ROOT / "data"


def test_validate_cli_without_services():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--validate"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_broken_copied_json_reports_filename(tmp_path):
    copy = tmp_path / "data"
    shutil.copytree(DATA, copy)
    broken = copy / "programs_floor" / "programs.json"
    broken.write_text("{broken", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--validate", "--data-dir", str(copy)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "programs.json" in result.stderr


async def test_users_seed_twice_preserves_id_and_hash(monkeypatch):
    rows = {}
    writes = []

    async def get_user(_session, email):
        return rows.get(email)

    async def upsert(_session, user_id, email, password_hash):
        writes.append(email)
        rows[email] = SimpleNamespace(id=user_id, password_hash=password_hash)

    monkeypatch.setattr(users, "get_user_by_email", get_user)
    monkeypatch.setattr(users, "upsert_user", upsert)
    monkeypatch.setattr(users, "hash_password", lambda raw: f"hashed:{raw}")
    monkeypatch.setattr(
        users, "verify_password", lambda raw, hashed: hashed == f"hashed:{raw}"
    )
    assert await users.seed_users(object(), DATA / "users.json") == 1
    assert await users.seed_users(object(), DATA / "users.json") == 1
    assert writes == ["demo@quack.kz"]
    assert rows["demo@quack.kz"].id == uuid5(NAMESPACE_URL, "demo@quack.kz")
    assert rows["demo@quack.kz"].password_hash != "quack-demo"


async def test_program_seed_twice_has_distinct_demo_records(monkeypatch):
    rows = {}

    async def upsert(_session, program):
        rows[program.id] = program

    monkeypatch.setattr(programs, "upsert_program", upsert)
    path = DATA / "programs_floor" / "programs.json"
    count = len(programs.validate_programs_floor(path))
    assert count >= 20
    assert await programs.seed_programs_floor(object(), path) == count
    assert await programs.seed_programs_floor(object(), path) == count
    assert len(rows) == count
    assert 8 <= [record.country for record in rows.values()].count("KZ") <= 10
    assert all(record.is_demo for record in rows.values())


async def test_calendar_records_remain_explicitly_demo():
    path = DATA / "knowledge_base" / "calendars.json"
    records = calendars.validate_calendars(path)
    assert {record.exam_id for record in records} == {"SAT_MATH", "ENT_MATH"}
    assert all(record.is_demo for record in records)
