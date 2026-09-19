"""T22–T23: the demo is prepared from inputs, and stays derivable (§11 A5, D06)."""

import json
from pathlib import Path

import pytest

from app.seed import demo as demo_seed

pytestmark = pytest.mark.phase5

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@pytest.fixture
def manifest():
    return demo_seed.validate_manifest(DATA_DIR)


def test_the_two_accounts_are_separate_students(manifest):
    prepared = demo_seed.student_id_of(str(manifest.users.prepared.email))
    clean = demo_seed.student_id_of(str(manifest.users.clean.email))
    assert prepared != clean


def test_the_demo_only_states_inputs_never_results(manifest):
    """Профиль и сохранённые программы — ввод; конфликт и знания выводятся."""
    paths = {step.path for step in manifest.prepared.profile}
    assert paths
    for path in paths:
        section = path.split(".", 1)[0]
        assert section in {
            "level",
            "direction",
            "academics",
            "preferences",
            "constraints",
            "priorities",
            "pace",
        }, path
    raw = json.loads((DATA_DIR / demo_seed.MANIFEST).read_text(encoding="utf-8"))
    # Only the data sections, not the prose: the manifest may *talk* about
    # knowledge states, it just must not carry any.
    data = {
        "prepared": {
            key: value
            for key, value in raw["prepared"].items()
            if key in {"profile", "traits", "saved_programs"}
        },
        "clean": {key: value for key, value in raw["clean"].items() if key != "why"},
    }
    serialized = json.dumps(data, ensure_ascii=False)
    for forbidden in (
        "knowledge_state",
        "p_at_obs",
        "evidence",
        "half_life",
        "answered",
        "correct",
        "diagnostic_run",
    ):
        assert forbidden not in serialized, forbidden


def test_the_conflict_follows_from_the_checked_in_programs(manifest):
    """Если правят дедлайн в programs.json — падает здесь, а не на защите."""
    programs = {
        item["id"]: item
        for item in json.loads(
            (DATA_DIR / "programs_floor" / "programs.json").read_text(encoding="utf-8")
        )
    }
    expected = manifest.prepared.expected
    same_day = [
        pid
        for pid in manifest.prepared.saved_programs
        if any(
            deadline["kind"] == "application"
            and deadline["date"] == expected.conflict_date
            for deadline in programs[pid]["deadlines"]
        )
    ]
    assert len(same_day) >= 2


def test_a_broken_conflict_expectation_fails_validation(tmp_path):
    raw = json.loads((DATA_DIR / demo_seed.MANIFEST).read_text(encoding="utf-8"))
    raw["prepared"]["expected"]["conflict_date"] = "2099-01-01"
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "manifest.json").write_text(
        json.dumps(raw, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "programs_floor").mkdir()
    (tmp_path / "programs_floor" / "programs.json").write_text(
        (DATA_DIR / "programs_floor" / "programs.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="not derivable"):
        demo_seed.validate_manifest(tmp_path)


def test_an_unknown_saved_program_fails_validation(tmp_path):
    raw = json.loads((DATA_DIR / demo_seed.MANIFEST).read_text(encoding="utf-8"))
    raw["prepared"]["saved_programs"] = ["does-not-exist"]
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "manifest.json").write_text(
        json.dumps(raw, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "programs_floor").mkdir()
    (tmp_path / "programs_floor" / "programs.json").write_text(
        (DATA_DIR / "programs_floor" / "programs.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown programs"):
        demo_seed.validate_manifest(tmp_path)


def test_t23_the_six_task_check_is_a_run_parameter_not_a_lowered_ceiling(manifest):
    from app.config import KnowledgeParams

    assert manifest.clean.diagnostic.n_tasks == 6
    # Глобальный потолок остаётся прежним: демо не меняет продукт для всех.
    assert KnowledgeParams().diag_max == 12
    assert manifest.clean.diagnostic.n_tasks <= KnowledgeParams().diag_max


def test_the_report_never_prints_a_password(manifest):
    report = demo_seed.DemoReport(created_users=[str(manifest.users.clean.email)])
    text = "\n".join(report.lines())
    assert manifest.users.prepared.password not in text
    assert manifest.users.clean.password not in text


def test_demo_check_reports_not_ready_when_something_is_missing():
    """Выход `--demo-check` — это gate, а не печать: не готово → код 1."""
    status = demo_seed.DemoStatus()
    status.add(True, "accounts")
    assert status.ready is True

    status.add(False, "ready generated texts: 0")
    assert status.ready is False
    assert any(line.startswith("[!!]") for line in status.lines)

    # Информационная строка вердикт не меняет.
    status = demo_seed.DemoStatus()
    status.lines.append("[..] job intents still active: 3")
    assert status.ready is True
