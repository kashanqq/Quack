"""Exact values of the frozen Redis key contract."""

import pytest

from app import keys


@pytest.mark.parametrize(
    ("factory", "args", "expected"),
    [
        (keys.session, ("student-1",), "quack:session:student-1"),
        (keys.llm_status, (), "quack:llm:status"),
        (keys.llm_ratelimit, ("chat",), "quack:llm:ratelimit:chat"),
        (keys.login_ratelimit, ("127.0.0.1",), "quack:auth:rl:127.0.0.1"),
        (
            keys.knowledge_version,
            ("student-1",),
            "quack:knowledge:version:student-1",
        ),
        (
            keys.ctx_topic,
            ("student-1", "skill-2"),
            "quack:ctx:topic:student-1:skill-2",
        ),
        (keys.lock, ("example",), "quack:lock:example"),
        (
            keys.forecast,
            ("student-1", "SAT_MATH"),
            "quack:forecast:student-1:SAT_MATH",
        ),
        (keys.lock, ("rebuild:student-1",), "quack:lock:rebuild:student-1"),
    ],
)
def test_exact_key(factory, args, expected):
    assert factory(*args) == expected
