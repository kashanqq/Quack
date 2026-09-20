"""T25: `status=ok` alone is not a release smoke (§22, AC10)."""

import io
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.phase5

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import check_release  # noqa: E402


def _body(**fields) -> io.BytesIO:
    payload = {"status": "ok", "checks": {}, "llm_status": "ok", "version": "abc123"}
    payload.update(fields)
    return io.BytesIO(json.dumps(payload).encode())


@pytest.fixture
def respond(monkeypatch):
    def _set(**fields):
        class _Response:
            def __init__(self):
                self._stream = _body(**fields)

            def read(self, *args):
                return self._stream.read(*args)

            def __enter__(self):
                return self._stream

            def __exit__(self, *_args):
                return None

        monkeypatch.setattr(
            check_release.urllib.request, "urlopen", lambda *a, **k: _Response()
        )

    return _set


def test_a_healthy_service_on_the_released_sha_passes(respond):
    respond(version="abc123")
    ok, note = check_release.probe("https://example.test/health", "abc123")
    assert ok
    assert "abc123" in note


def test_a_healthy_service_on_the_previous_sha_fails(respond):
    """Старая, совершенно здоровая версия отвечает точно так же."""
    respond(version="oldsha")
    ok, note = check_release.probe("https://example.test/health", "abc123")
    assert not ok
    assert "oldsha" in note and "abc123" in note


def test_a_degraded_200_is_not_a_successful_release(respond):
    respond(status="degraded", checks={"neo4j": "down"})
    ok, note = check_release.probe("https://example.test/health", "abc123")
    assert not ok
    assert "degraded" in note


def test_an_unreachable_service_fails_without_leaking_anything(monkeypatch):
    def boom(*_args, **_kwargs):
        raise check_release.urllib.error.URLError("connection refused")

    monkeypatch.setattr(check_release.urllib.request, "urlopen", boom)
    ok, note = check_release.probe("https://example.test/health", "abc123")
    assert not ok
    assert note.startswith("unreachable")


def test_without_an_expected_sha_only_status_is_checked(respond):
    respond(version="whatever")
    ok, _note = check_release.probe("https://example.test/health", "")
    assert ok
