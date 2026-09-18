"""Saved-program HTTP status, event, and isolation contracts."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import saved as saved_api
from app.api.auth import issue_token
from app.errors import Conflict, NotFound
from app.events import store
from app.main import create_app
from app.schemas.programs import Program, SavedProgram

pytestmark = pytest.mark.phase1


def _program() -> Program:
    return Program(
        id="program-1",
        university="Test University",
        country="KZ",
        city="Almaty",
        direction="CS",
        language="en",
        currency="KZT",
        requirements=[],
        deadlines=[],
        source_url="https://example.test/program-1",
        checked_at=date(2026, 1, 1),
        is_demo=True,
        extracted_auto=False,
        flagged=False,
    )


@pytest.fixture
def saved_app(monkeypatch):
    app = create_app()
    program = _program()
    saved: dict[tuple, SavedProgram] = {}
    events = []

    async def session_override():
        yield object()

    async def list_saved(session, student_id):
        return [item for (owner, _), item in saved.items() if owner == student_id]

    async def get_program(session, program_id):
        return program if program_id == program.id else None

    async def save_program(session, student_id, program_id):
        if program_id != program.id:
            raise NotFound("program not found")
        key = student_id, program_id
        if key in saved:
            raise Conflict("program already saved")
        saved[key] = SavedProgram(program_id=program_id, saved_at=datetime.now(UTC))

    async def remove_saved(session, student_id, program_id):
        if saved.pop((student_id, program_id), None) is None:
            raise NotFound("saved program not found")

    async def append_event(session, redis, event):
        events.append(event)

    app.dependency_overrides[deps.get_session] = session_override
    app.dependency_overrides[deps.get_redis] = lambda: object()
    monkeypatch.setattr(saved_api.program_repo, "list_saved", list_saved)
    monkeypatch.setattr(saved_api.program_repo, "get_program", get_program)
    monkeypatch.setattr(saved_api.program_repo, "save_program", save_program)
    monkeypatch.setattr(saved_api.program_repo, "remove_saved", remove_saved)
    monkeypatch.setattr(store, "append", append_event)
    return app, events


def test_saved_lifecycle_and_second_student_isolation(saved_app):
    app, events = saved_app
    first_id, second_id = uuid4(), uuid4()
    with TestClient(app) as client:
        assert client.get("/saved").status_code == 401
        assert client.post("/saved/program-1").status_code == 401
        client.cookies.set("quack_token", issue_token(first_id, "first@quack.kz"))
        created = client.post("/saved/program-1")
        duplicate = client.post("/saved/program-1")
        listed = client.get("/saved")
        client.cookies.set("quack_token", issue_token(second_id, "second@quack.kz"))
        isolated = client.get("/saved")
        client.cookies.set("quack_token", issue_token(first_id, "first@quack.kz"))
        deleted = client.delete("/saved/program-1")
        missing = client.delete("/saved/program-1")

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["program"]["id"] == "program-1"
    assert isolated.json() == {"items": [], "total": 0}
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert [event.type.value for event in events] == [
        "program.saved",
        "program.removed",
    ]
    assert all(event.student_id == first_id for event in events)
    assert all(event.payload == {"program_id": "program-1"} for event in events)


def test_missing_program_and_wrong_content_type(saved_app):
    app, events = saved_app
    with TestClient(app) as client:
        client.cookies.set("quack_token", issue_token(uuid4(), "first@quack.kz"))
        missing = client.post("/saved/nope")
        wrong_type = client.post(
            "/saved/program-1", content="plain", headers={"Content-Type": "text/plain"}
        )

    assert missing.status_code == 404
    assert wrong_type.status_code == 415
    assert wrong_type.json()["error"]["code"] == "unsupported_media_type"
    assert events == []
