"""Shared test fixtures for B3 and future B2 integration tests."""

import fakeredis.aioredis
import pytest

from app.llm.fake import FakeLLMClient


@pytest.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis()
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def fake_llm():
    return FakeLLMClient()
