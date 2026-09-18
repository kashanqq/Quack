"""Health, request middleware and log redaction contracts."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import health as health_module
from app.logging import mask_secrets
from app.main import create_app

pytestmark = pytest.mark.phase2
ORIGINAL_GRAPH_PENDING = health_module._graph_pending


@pytest.fixture(autouse=True)
def no_pending_events(monkeypatch):
    async def count(_request):
        return 0

    monkeypatch.setattr(health_module, "_graph_pending", count)


@pytest.mark.parametrize("llm_status", ["ok", "degraded", "down"])
def test_health_all_storage_ok(monkeypatch, fake_llm, llm_status):
    fake_llm.forced_status = llm_status

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
            "search": "skipped",
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
def test_graph_pending_is_recent_count_and_zero_is_omitted(monkeypatch, pending):
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


async def test_graph_pending_query_counts_unprocessed_last_hour():
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
    assert "events.ingested_at >=" in sql
