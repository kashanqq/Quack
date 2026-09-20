"""Health, request middleware and log redaction contracts."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import health as health_module
from app.logging import mask_secrets
from app.main import create_app

pytestmark = pytest.mark.phase2
ORIGINAL_GRAPH_PENDING = health_module._graph_pending
ORIGINAL_SEARCH = health_module._search


@pytest.fixture(autouse=True)
def no_pending_events(monkeypatch):
    async def count(_request):
        return 0

    monkeypatch.setattr(health_module, "_graph_pending", count)
    monkeypatch.setattr(health_module, "_jobs_pending", count)


@pytest.fixture
def search_status(monkeypatch):
    """Pin `checks.search` — otherwise the answer depends on whether the
    machine running the tests happens to have Redis up, which is what made
    these assertions pass locally and fail in CI."""

    def _set(value):
        async def status(_request):
            return value

        monkeypatch.setattr(health_module, "_search", status)

    return _set


@pytest.mark.parametrize("llm_status", ["ok", "degraded", "down"])
def test_health_all_storage_ok(monkeypatch, fake_llm, search_status, llm_status):
    fake_llm.forced_status = llm_status
    search_status("ok")

    async def healthy(_request):
        return True

    monkeypatch.setattr(health_module, "_postgres", healthy)
    monkeypatch.setattr(health_module, "_neo4j", healthy)
    monkeypatch.setattr(health_module, "_redis", healthy)
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "postgres": "ok",
            "neo4j": "ok",
            "redis": "ok",
            "search": "ok",
        },
        "llm_status": llm_status,
        "version": "dev",
    }


def test_health_one_storage_down_is_degraded(monkeypatch):
    async def healthy(_request):
        return True

    async def unhealthy(_request):
        raise OSError("private connection string")

    monkeypatch.setattr(health_module, "_postgres", healthy)
    monkeypatch.setattr(health_module, "_neo4j", unhealthy)
    monkeypatch.setattr(health_module, "_redis", healthy)
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["neo4j"] == "down"
    assert "private connection string" not in response.text


def test_json_content_type_required_for_nonempty_mutation():
    with TestClient(create_app()) as client:
        response = client.post(
            "/missing", content="plain", headers={"Content-Type": "text/plain"}
        )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"
    assert "X-Request-Id" in response.headers


def test_log_processor_masks_nested_secret_keys():
    event = {
        "request_id": "visible",
        "Authorization": "Bearer private",
        "nested": [{"db_password": "private", "api_key": "private"}],
    }
    assert mask_secrets(None, "info", event) == {
        "request_id": "visible",
        "Authorization": "[REDACTED]",
        "nested": [{"db_password": "[REDACTED]", "api_key": "[REDACTED]"}],
    }


@pytest.mark.parametrize("pending", [0, 3])
def test_graph_pending_is_the_backlog_and_zero_is_omitted(
    monkeypatch, search_status, pending
):
    search_status("ok")

    async def healthy(_request):
        return True

    async def count(_request):
        return pending

    monkeypatch.setattr(health_module, "_postgres", healthy)
    monkeypatch.setattr(health_module, "_neo4j", healthy)
    monkeypatch.setattr(health_module, "_redis", healthy)
    monkeypatch.setattr(health_module, "_graph_pending", count)
    with TestClient(create_app()) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"].get("graph_pending") == (pending or None)
    assert "payload" not in response.text


async def test_graph_pending_counts_the_whole_recoverable_backlog():
    """Phase 5 (§19): not "the last hour", and not raw chat messages."""
    statements = []

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def scalar(self, statement):
            statements.append(statement)
            return 4

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(sessionmaker=Session))
    )
    assert await ORIGINAL_GRAPH_PENDING(request) == 4
    sql = str(statements[0])
    assert "events.processed_at IS NULL" in sql
    assert "ingested_at" not in sql
    assert "events.type IN" in sql


async def test_search_status_is_read_not_probed():
    """`skipped` when nothing is known — never dressed up as `ok` (§10)."""
    from app import keys

    class FakeRedis:
        def __init__(self, values):
            self.values = values

        async def get(self, key):
            return self.values.get(key)

    def request_with(values):
        return SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(redis=FakeRedis(values)))
        )

    assert await ORIGINAL_SEARCH(request_with({})) == "skipped"
    assert await ORIGINAL_SEARCH(request_with({keys.search_last_ok(): "t"})) == "ok"
    assert (
        await ORIGINAL_SEARCH(
            request_with({keys.search_last_error(): "boom", keys.search_last_ok(): "t"})
        )
        == "down"
    )
    no_redis = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=None)))
    assert await ORIGINAL_SEARCH(no_redis) == "skipped"
