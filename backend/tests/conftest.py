"""Shared test fixtures for B3 and future B2 integration tests."""

import fakeredis.aioredis
import pytest


@pytest.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis()
    try:
        yield client
    finally:
        await client.aclose()


# TODO(B2): add fake_llm when app.llm.fake.FakeLLMClient is merged.
