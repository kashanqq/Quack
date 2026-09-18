"""Profile HTTP behavior and student-scoped event creation."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api.auth import issue_token
from app.events import store
from app.main import create_app

pytestmark = pytest.mark.phase1


class ProfileSession:
    def __init__(self) -> None:
        self.rows = {}
        self.operations: list[str] = []

    async def get(self, model, student_id):
        return self.rows.get(student_id)

    def add(self, row):
        self.rows[row.student_id] = row

    async def flush(self):
        self.operations.append("profile_flushed")


@pytest.fixture
def profile_app(monkeypatch):
    app = create_app()
    session = ProfileSession()
    events = []

    async def session_override():
        yield session

    async def append_event(db, redis, event):
        session.operations.append("event_appended")
        events.append(event)

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_redis] = lambda: object()
    monkeypatch.setattr(store, "append", append_event)
    return app, session, events


def test_new_profile_defaults_and_student_isolation(profile_app):
    app, _, _ = profile_app
    first_id, second_id = uuid4(), uuid4()
    with TestClient(app) as client:
        assert client.get("/profile").status_code == 401
        client.cookies.set("quack_token", issue_token(first_id, "first@quack.kz"))
        first = client.get("/profile")
        client.cookies.set("quack_token", issue_token(second_id, "second@quack.kz"))
        second = client.get("/profile")

    for response, student_id in ((first, first_id), (second, second_id)):
        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == str(student_id)
        assert data["readiness"] == 0.0
        for section in data["questionnaire"].values():
            for field in section.values():
                assert field["value"] is None
                assert field["mark"] == "default"


def test_patch_updates_profile_then_appends_one_event(profile_app):
    app, session, events = profile_app
    student_id = uuid4()
    with TestClient(app) as client:
        client.cookies.set("quack_token", issue_token(student_id, "first@quack.kz"))
        response = client.patch(
            "/profile",
            json={"path": "preferences.countries", "value": ["DE", "NL"], "by": "user"},
        )

    assert response.status_code == 200
    field = response.json()["questionnaire"]["preferences"]["countries"]
    assert field["value"] == ["DE", "NL"]
    assert field["mark"] == "stated"
    assert response.json()["readiness"] > 0
    assert session.operations == ["profile_flushed", "event_appended"]
    assert len(events) == 1
    assert events[0].student_id == student_id
    assert events[0].type == "profile.updated"
    assert events[0].payload == {
        "field": "preferences.countries",
        "value": ["DE", "NL"],
        "by": "user",
    }


def test_invalid_profile_path_does_not_append_event(profile_app):
    app, _, events = profile_app
    with TestClient(app) as client:
        client.cookies.set("quack_token", issue_token(uuid4(), "first@quack.kz"))
        response = client.patch(
            "/profile", json={"path": "unknown.path", "value": 1, "by": "user"}
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"
    assert events == []
