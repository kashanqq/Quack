"""Program read routes, filters, pagination, and authentication."""

from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import programs as programs_api
from app.api.auth import issue_token
from app.main import create_app
from app.schemas.common import Page
from app.schemas.programs import Program

pytestmark = pytest.mark.phase1


def _program(program_id: str, country: str) -> Program:
    return Program(
        id=program_id,
        university="Test University",
        country=country,
        city="Test City",
        direction="CS",
        language="en",
        currency="USD",
        requirements=[],
        deadlines=[],
        source_url=f"https://example.test/{program_id}",
        checked_at=date(2026, 1, 1),
        is_demo=True,
        extracted_auto=False,
        flagged=False,
    )


@pytest.fixture
def programs_app(monkeypatch):
    app = create_app()
    programs = [_program("kz-1", "KZ"), _program("kz-2", "KZ"), _program("de-1", "DE")]
    calls = []

    async def session_override():
        yield object()

    async def get_program(session, program_id):
        return next((item for item in programs if item.id == program_id), None)

    async def list_programs(session, country=None, direction=None, limit=50, offset=0):
        calls.append((country, direction, limit, offset))
        matching = [
            item
            for item in programs
            if (country is None or item.country == country)
            and (direction is None or item.direction == direction)
        ]
        return Page[Program](
            items=matching[offset : offset + limit], total=len(matching)
        )

    app.dependency_overrides[deps.get_session] = session_override
    monkeypatch.setattr(programs_api.program_repo, "get_program", get_program)
    monkeypatch.setattr(programs_api.program_repo, "list_programs", list_programs)
    return app, calls


def test_program_detail_and_not_found(programs_app):
    app, _ = programs_app
    with TestClient(app) as client:
        assert client.get("/programs/kz-1").status_code == 401
        client.cookies.set("quack_token", issue_token(uuid4(), "student@quack.kz"))
        found = client.get("/programs/kz-1")
        missing = client.get("/programs/nope")

    assert found.status_code == 200
    assert found.json()["id"] == "kz-1"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_program_filters_pagination_and_validation(programs_app):
    app, calls = programs_app
    with TestClient(app) as client:
        client.cookies.set("quack_token", issue_token(uuid4(), "student@quack.kz"))
        default = client.get("/programs")
        country = client.get("/programs", params={"country": "KZ", "limit": 1})
        offset = client.get("/programs", params={"country": "KZ", "offset": 1})
        invalid = client.get("/programs", params={"limit": 101})
        negative = client.get("/programs", params={"offset": -1})

    assert default.status_code == 200
    assert default.json()["total"] == 3
    assert country.json()["total"] == 2
    assert [item["id"] for item in country.json()["items"]] == ["kz-1"]
    assert [item["id"] for item in offset.json()["items"]] == ["kz-2"]
    assert calls[0] == (None, None, 50, 0)
    assert invalid.status_code == negative.status_code == 400
    assert invalid.json()["error"]["code"] == "validation_failed"
