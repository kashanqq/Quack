"""Health, request middleware and log redaction contracts."""

from fastapi.testclient import TestClient

from app.api import health as health_module
from app.logging import mask_secrets
from app.main import create_app


def test_health_all_storage_ok(monkeypatch):
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
        "llm_status": "down",
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
