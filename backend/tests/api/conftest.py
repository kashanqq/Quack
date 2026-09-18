"""API unit tests use B2's fake client during the real application lifespan."""

import pytest

from app.llm import client as llm_client


@pytest.fixture(autouse=True)
def use_fake_llm(monkeypatch, fake_llm):
    monkeypatch.setattr(llm_client, "LLMClient", lambda _settings, _redis: fake_llm)
