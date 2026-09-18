"""Diagnostic and mock routes delegate state transitions to B1 apply."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps, diagnostic, mocks
from app.config import KnowledgeParams
from app.events.dispatch import RuleDeps
from app.main import create_app
from app.schemas.auth import StudentCtx
from app.schemas.diagnostic import DiagnosticOut, DiagnosticResult, DiagnosticState
from app.schemas.mocks import MockOut, MockResultOut
from app.schemas.tasks import AnswerResult, Grade

pytestmark = pytest.mark.phase2


class FakeSession:
    def __init__(self):
        self.diagnostic = None
        self.mock = None

    async def scalar(self, statement):
        return (
            self.diagnostic
            if self.diagnostic and self.diagnostic.status == "active"
            else None
        )

    async def get(self, model, run_id):
        if model is diagnostic.DiagnosticRun:
            return (
                self.diagnostic
                if self.diagnostic and self.diagnostic.id == run_id
                else None
            )
        return self.mock if self.mock and self.mock.id == run_id else None


class FakeRedis:
    async def get(self, key):
        return b"7"


@pytest.fixture
def transport():
    student = StudentCtx(student_id=uuid4(), email="student@example.com")
    session = FakeSession()
    rule_deps = RuleDeps(
        graph=object(),
        redis=FakeRedis(),
        params=KnowledgeParams(),
        now=lambda: datetime(2026, 9, 18, tzinfo=UTC),
    )
    app = create_app()

    async def session_override():
        yield session

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_current_student] = lambda: student
    app.dependency_overrides[deps.get_rule_deps] = lambda: rule_deps
    return TestClient(app), student, session, rule_deps


def _diagnostic(student, session, instance_id):
    state = DiagnosticState(
        exam_id="SAT_MATH",
        budget_left=7,
        reserve_left=4,
        asked=[instance_id],
        answered=0,
        pending_descent=[],
        reask_queue=[],
        roots_found=[],
        trap_hits=[],
        firm=[],
        shaky=[],
        last_grade_correct=None,
    )
    row = SimpleNamespace(
        id=uuid4(),
        student_id=student.student_id,
        exam_id="SAT_MATH",
        status="active",
        state=state.model_dump(mode="json"),
    )
    session.diagnostic = row
    return row, DiagnosticOut(
        run_id=row.id, status="active", state=state, next_task=None
    )


def _mock(student, session, instance_id):
    row = SimpleNamespace(
        id=uuid4(),
        student_id=student.student_id,
        exam_id="SAT_MATH",
        kind="mock_set",
        status="active",
        instance_ids=[instance_id],
        section_name="Math",
        predicted_before=700.0,
    )
    session.mock = row
    return row, MockOut(
        run_id=row.id,
        kind="mock_set",
        exam_id="SAT_MATH",
        section_name="Math",
        status="active",
        tasks=[],
        minutes=30,
        answered=0,
        predicted_before=700.0,
    )


def _answer_result():
    return AnswerResult(
        grade=Grade(correct=True),
        solution=[],
        state_words="done",
        knowledge_version=7,
    )


def test_diagnostic_start_active_and_limits(transport, monkeypatch):
    client, student, session, _ = transport
    instance_id = uuid4()
    row, output = _diagnostic(student, session, instance_id)
    session.diagnostic = None
    calls = []

    async def start(*args):
        calls.append(args[-1])
        session.diagnostic = row
        return output

    monkeypatch.setattr(diagnostic.apply_diagnostic, "start", start)
    assert (
        client.post(
            "/diagnostic", json={"exam_id": "SAT_MATH", "n_tasks": 13}
        ).status_code
        == 400
    )
    response = client.post("/diagnostic", json={"exam_id": "SAT_MATH", "n_tasks": 3})
    assert (
        response.status_code == 201 and response.headers["X-Knowledge-Version"] == "7"
    )
    assert calls == [3]
    response = client.post("/diagnostic", json={"exam_id": "SAT_MATH", "n_tasks": 3})
    assert (
        response.status_code == 409
        and str(row.id) in response.json()["error"]["message"]
    )
    monkeypatch.setattr(diagnostic, "_out", lambda *args: _async(output))
    assert client.get("/diagnostic/active?exam_id=SAT_MATH").status_code == 200
    session.diagnostic = None
    assert client.get("/diagnostic/active?exam_id=SAT_MATH").status_code == 404


async def _async(value):
    return value


def test_diagnostic_answer_finish_and_ownership(transport, monkeypatch):
    client, student, session, _ = transport
    instance_id = uuid4()
    row, output = _diagnostic(student, session, instance_id)
    events = []

    async def record(*args):
        events.append("task.answered")
        assert args[-1] == "diagnostic"
        return _answer_result()

    async def answer(*args):
        assert args[-1].grade.correct
        return output

    async def finish(*args):
        events.append("diagnostic.completed")
        return DiagnosticResult(
            firm=[], shaky=[], roots=[], suspected=[], start_from=[], words="done"
        )

    monkeypatch.setattr(diagnostic, "record_answer", record)
    monkeypatch.setattr(diagnostic.apply_diagnostic, "answer", answer)
    monkeypatch.setattr(diagnostic.apply_diagnostic, "finish", finish)
    body = {
        "instance_id": str(instance_id),
        "answer": "A",
        "time_spent_sec": 10,
        "mode": "diagnostic",
    }
    assert client.post(f"/diagnostic/{uuid4()}/answer", json=body).status_code == 404
    wrong = {**body, "instance_id": str(uuid4())}
    assert client.post(f"/diagnostic/{row.id}/answer", json=wrong).status_code == 404
    response = client.post(f"/diagnostic/{row.id}/answer", json=body)
    assert (
        response.status_code == 200 and response.headers["X-Knowledge-Version"] == "7"
    )
    assert events == ["task.answered"]
    response = client.post(f"/diagnostic/{row.id}/finish")
    assert (
        response.status_code == 200 and response.headers["X-Knowledge-Version"] == "7"
    )
    assert events == ["task.answered", "diagnostic.completed"]


def test_mock_start_get_answer_finish(transport, monkeypatch):
    client, student, session, _ = transport
    instance_id = uuid4()
    row, output = _mock(student, session, instance_id)
    session.mock = None
    events = []

    async def start(*args):
        session.mock = row
        return output

    async def record(*args):
        events.append("task.answered")
        assert args[-1] == "mock_set"
        return _answer_result()

    async def answer(*args):
        assert args[-1].grade.correct
        return output

    async def finish(*args):
        events.append("mock.completed")
        return MockResultOut(
            run_id=row.id,
            raw_score=1,
            max_raw=1,
            scaled_score=800,
            scale_note=None,
            per_skill=[],
            brier_point=None,
            correct=True,
        )

    monkeypatch.setattr(mocks.apply_mocks, "start", start)
    monkeypatch.setattr(mocks, "_out", lambda *args: _async(output))
    monkeypatch.setattr(mocks, "record_answer", record)
    monkeypatch.setattr(mocks.apply_mocks, "answer", answer)
    monkeypatch.setattr(mocks.apply_mocks, "finish", finish)
    start_body = {
        "kind": "mock_set",
        "exam_id": "SAT_MATH",
        "set_id": None,
        "skill_id": None,
        "misconception_id": None,
    }
    response = client.post("/mocks", json=start_body)
    assert (
        response.status_code == 201 and response.headers["X-Knowledge-Version"] == "7"
    )
    assert client.get(f"/mocks/{row.id}").status_code == 200
    assert client.get(f"/mocks/{uuid4()}").status_code == 404
    body = {
        "instance_id": str(instance_id),
        "answer": "A",
        "time_spent_sec": 10,
        "mode": "mock_set",
    }
    wrong = {**body, "instance_id": str(uuid4())}
    assert client.post(f"/mocks/{row.id}/answer", json=wrong).status_code == 404
    response = client.post(f"/mocks/{row.id}/answer", json=body)
    assert (
        response.status_code == 200 and response.headers["X-Knowledge-Version"] == "7"
    )
    assert events == ["task.answered"]
    response = client.post(f"/mocks/{row.id}/finish")
    assert (
        response.status_code == 200 and response.headers["X-Knowledge-Version"] == "7"
    )
    assert events == ["task.answered", "mock.completed"]


def test_run_reads_render_pending_tasks(transport, monkeypatch):
    client, student, session, _ = transport
    instance_id = uuid4()
    diagnostic_row, _ = _diagnostic(student, session, instance_id)
    mock_row, _ = _mock(student, session, instance_id)
    instance = SimpleNamespace(
        id=instance_id,
        template_id="task-1",
        exam_id="SAT_MATH",
        type="mcq4",
        skill_id="algebra",
        stem_rendered="2 + 2?",
        options=[{"key": "A", "text": "4"}],
        figure_url=None,
        time_reference_sec=60,
        difficulty=1,
        tags=[],
        answered_at=None,
    )
    monkeypatch.setattr(diagnostic, "owned_instance", lambda *args: _async(instance))
    monkeypatch.setattr(mocks, "owned_instance", lambda *args: _async(instance))
    section = SimpleNamespace(name="Math", minutes=30)
    exam_format = SimpleNamespace(sections=[section])
    monkeypatch.setattr(
        mocks.canonical, "get_exam_format", lambda *args: _async(exam_format)
    )
    response = client.get("/diagnostic/active?exam_id=SAT_MATH")
    assert response.status_code == 200, response.text
    assert response.json()["next_task"]["id"] == str(instance_id)
    assert response.headers["X-Knowledge-Version"] == "7"
    response = client.get(f"/mocks/{mock_row.id}")
    assert response.status_code == 200, response.text
    assert response.json()["tasks"][0]["id"] == str(instance_id)
    assert response.json()["minutes"] == 30
    assert response.headers["X-Knowledge-Version"] == "7"
    diagnostic_row.student_id = uuid4()
    assert client.post(f"/diagnostic/{diagnostic_row.id}/finish").status_code == 404
    mock_row.student_id = uuid4()
    assert client.get(f"/mocks/{mock_row.id}").status_code == 404
