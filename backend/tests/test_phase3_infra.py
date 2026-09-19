"""Phase-3 infrastructure: worker embedder, layers, settings, keys
(docs/tz/phase3-agents.md §2.5, §3.12, §6.11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import keys
from app.config import KnowledgeParams, Settings
from app.workers import main as workers
from tests.test_layers import APP_ROOT, _check_imports

pytestmark = pytest.mark.phase3


async def test_worker_startup_loads_embedder_or_none(monkeypatch):
    class Broken:
        def __init__(self, *_a):
            raise RuntimeError("no model")

    monkeypatch.setattr("app.embeddings.Embedder", Broken)
    ctx: dict = {}
    await workers.load_embedder(ctx)
    assert ctx["embedder"] is None

    class Works:
        def __init__(self, *_a):
            self.calls = []

        def embed(self, texts):
            self.calls.append(texts)
            return [[0.0] * 384]

    monkeypatch.setattr("app.embeddings.Embedder", Works)
    await workers.load_embedder(ctx)
    assert ctx["embedder"].calls == [["warmup"]]
    assert workers.WorkerInteractive.on_startup is workers.startup_interactive
    assert workers.WorkerBulk.on_startup is workers.startup


def test_layers_apply_has_no_arq_and_agents_no_api():
    _check_imports("apply", ("arq", "app.agents", "app.llm", "app.workers"))
    _check_imports("agents", ("app.api",))
    _check_imports("graph", ("app.agents", "app.llm", "app.db", "app.apply"))


def test_single_llm_client():
    hits = [
        path.relative_to(APP_ROOT).as_posix()
        for path in APP_ROOT.rglob("*.py")
        if "AsyncOpenAI(" in path.read_text(encoding="utf-8")
    ]
    assert hits == ["llm/client.py"]


def test_phase3_settings_and_params():
    params = KnowledgeParams()
    assert params.observer_window_max == 30
    assert params.assistant_max_questions == 2
    assert params.assistant_readiness_threshold == 0.6
    assert params.context_set_multiplier == 1.5
    assert params.tutor_escalate_after_failures == 2
    settings = Settings()
    assert settings.OBSERVER_SLOT == "bulk"
    assert settings.OBSERVER_JOB_TIMEOUT_S >= settings.LLM_TIMEOUT_BULK_S + 10
    assert (
        settings.CTX_CACHE_TTL_S,
        settings.CHAT_LOCK_TTL_S,
        settings.CANON_JOB_TIMEOUT_S,
    ) == (
        3600,
        120,
        30,
    )


def test_matching_snapshot_key():
    assert keys.matching_snapshot("s") == "quack:matching:snapshot:s"


def test_env_example_lists_new_settings():
    env = Path(__file__).resolve().parents[2] / "deploy" / ".env.example"
    if not env.exists():
        pytest.skip("no .env.example in this checkout")
    text = env.read_text(encoding="utf-8")
    for name in (
        "OBSERVER_SLOT",
        "CTX_CACHE_TTL_S",
        "CHAT_LOCK_TTL_S",
        "OBSERVER_JOB_TIMEOUT_S",
        "CANON_JOB_TIMEOUT_S",
    ):
        assert name in text
