"""Smoke tests for the application factory and HTTP contracts."""

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import NotFound
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


def test_create_app(app):
    assert isinstance(app, FastAPI)


def test_openapi_title(app):
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Quack API"


def test_unknown_route(app):
    with TestClient(app) as client:
        response = client.get("/unknown")
    assert response.status_code == 404
    assert re.fullmatch(r"[0-9a-f]{16}", response.headers["X-Request-Id"])


def test_app_error_contract(app):
    @app.get("/test-error")
    async def fail():
        raise NotFound("program not found")

    with TestClient(app) as client:
        response = client.get("/test-error", headers={"X-Request-Id": "error-id"})
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "program not found"}
    }
    assert response.headers["X-Request-Id"] == "error-id"


def test_request_validation_returns_400(app):
    @app.get("/test-validation")
    async def validate(value: int):
        return {"value": value}

    with TestClient(app) as client:
        response = client.get("/test-validation", params={"value": "not-an-int"})
    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "validation_failed", "message": "Request validation failed"}
    }
    assert "X-Request-Id" in response.headers


def test_temporary_health_and_incoming_request_id(app):
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-Id": "existing-id"})
    assert response.status_code == 200
    assert response.json() == {
        "status": "temporary",
        "message": "Service health checks are not implemented",
    }
    assert response.headers["X-Request-Id"] == "existing-id"


@pytest.mark.parametrize("request_id", [None, "failure-id"])
def test_unhandled_exception_hides_details_and_returns_request_id(app, request_id):
    @app.get("/test-unhandled")
    async def fail():
        raise RuntimeError("private exception details")

    headers = {"X-Request-Id": request_id} if request_id else {}
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-unhandled", headers=headers)
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal", "message": "Internal server error"}
    }
    if request_id:
        assert response.headers["X-Request-Id"] == request_id
    else:
        assert re.fullmatch(r"[0-9a-f]{16}", response.headers["X-Request-Id"])
