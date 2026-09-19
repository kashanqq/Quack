"""Phase-5 tests that start the real application lifespan use B2's fake client.

Same reason as `tests/api/conftest.py`: `create_app()` builds a real
`LLMClient` during startup, and that constructor needs a key. Without this the
tests pass on a developer machine that happens to have `LLM_API_KEY` in
`backend/.env` and fail in CI, which is precisely the environment-dependent
failure phase 5 had to fix in `test_health.py`.
"""

import pytest

from app.llm import client as llm_client


@pytest.fixture(autouse=True)
def use_fake_llm(monkeypatch, fake_llm):
    monkeypatch.setattr(llm_client, "LLMClient", lambda _settings, _redis: fake_llm)
