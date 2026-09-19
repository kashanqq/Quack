"""Per-student key/value state routes without external services."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps, state
from app.main import create_app
from app.schemas.auth import StudentCtx

pytestmark = pytest.mark.phase1


@pytest.fixture
def state_app(monkeypatch):
    app = create_app()
    student = StudentCtx(student_id=uuid4(), email="s@quack.kz")

    async def session_override():
        yield object()

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_current_student] = lambda: student
    repo = {
        "get_all": AsyncMock(return_value={"panel": {"w": 320}}),
        "patch": AsyncMock(),
        "clear": AsyncMock(),
    }
    for name, mock in repo.items():
        monkeypatch.setattr(state.state_repo, name, mock)
    return app, student, repo


def test_get_returns_the_stored_map(state_app):
    app, student, repo = state_app
    with TestClient(app) as client:
        response = client.get("/state")

    assert response.status_code == 200
    assert response.json() == {"panel": {"w": 320}}
    assert repo["get_all"].await_args.args[1] == student.student_id


def test_patch_passes_values_and_nulls_and_returns_204(state_app):
    app, student, repo = state_app
    with TestClient(app) as client:
        response = client.patch("/state", json={"a": [1, 2], "b": None})

    assert response.status_code == 204
    assert repo["patch"].await_args.args[1:] == (
        student.student_id,
        {"a": [1, 2], "b": None},
    )


def test_patch_rejects_too_many_or_empty_keys(state_app):
    app, _, repo = state_app
    with TestClient(app) as client:
        many = client.patch("/state", json={str(i): i for i in range(201)})
        empty = client.patch("/state", json={"": 1})

    assert many.status_code == empty.status_code == 400
    assert many.json()["error"]["code"] == "validation_failed"
    repo["patch"].assert_not_awaited()


def test_delete_clears_the_state(state_app):
    app, student, repo = state_app
    with TestClient(app) as client:
        response = client.delete("/state")

    assert response.status_code == 204
    assert repo["clear"].await_args.args[1] == student.student_id


def test_state_requires_a_session():
    with TestClient(create_app()) as client:
        assert client.get("/state").status_code == 401
