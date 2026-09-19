"""§10, §15: nothing is acknowledged before it is durable.

The failure this guards against is specific and easy to reintroduce: a
`yield` dependency that commits in its teardown runs *after* FastAPI has sent
the response, so a client can be told `202 accepted` and only afterwards have
the transaction fail. The commit therefore lives in the HTTP middleware
(`app/api/commit.py::commit_request`), between the endpoint and the response.
These tests pin that order and the two cases where the commit must not happen.
"""

from types import SimpleNamespace

import pytest

from app.api.commit import SESSION_ATTR, commit_request
from app.events.outbox import JobOutbox

pytestmark = pytest.mark.phase5


class _Session:
    def __init__(self, order: list[str], fail: bool = False) -> None:
        self.order = order
        self.fail = fail
        self.added: list = []

    def add(self, row):
        row.id = len(self.added) + 1
        self.added.append(row)

    async def scalar(self, *_args, **_kwargs):
        return None

    async def flush(self):
        return None

    async def commit(self):
        if self.fail:
            raise RuntimeError("commit failed")
        self.order.append("commit")

    async def rollback(self):
        self.order.append("rollback")


def _request(session, outbox: JobOutbox | None = None):
    state = SimpleNamespace()
    setattr(state, SESSION_ATTR, session)
    if outbox is not None:
        state.job_outbox = outbox
    return SimpleNamespace(
        state=state,
        app=SimpleNamespace(state=SimpleNamespace(sessionmaker=None, arq=None)),
    )


async def test_a_successful_response_commits():
    order: list[str] = []
    session = _Session(order)
    await commit_request(_request(session), 200)
    assert order == ["commit"]


async def test_a_failed_request_is_rolled_back_not_committed():
    """4xx/5xx — писать нечего: иначе половина неудачного запроса осядет."""
    order: list[str] = []
    session = _Session(order)
    await commit_request(_request(session), 409)
    assert order == ["rollback"]


async def test_a_broken_commit_rolls_back_and_raises():
    """Вызывающий превратит это в 500 — клиенту не скажут «принято»."""
    order: list[str] = []
    session = _Session(order, fail=True)
    with pytest.raises(RuntimeError):
        await commit_request(_request(session), 202)
    assert order == ["rollback"]


async def test_job_intents_are_written_in_that_same_transaction():
    """§9.2: событие и намерение задачи долговечны вместе или никак."""
    order: list[str] = []
    session = _Session(order)
    outbox = JobOutbox()
    outbox.enqueue("bulk", "soft_match", job_id="softmatch:1", student_id="s")

    await commit_request(_request(session, outbox), 202)

    assert [row.fn_name for row in session.added] == ["soft_match"]
    assert order == ["commit"]


async def test_a_failed_request_does_not_leave_job_intents_behind():
    order: list[str] = []
    session = _Session(order)
    outbox = JobOutbox()
    outbox.enqueue("bulk", "soft_match", job_id="softmatch:1", student_id="s")

    await commit_request(_request(session, outbox), 500)

    assert session.added == []
    assert order == ["rollback"]


async def test_the_session_is_only_committed_once():
    order: list[str] = []
    session = _Session(order)
    request = _request(session)
    await commit_request(request, 200)
    await commit_request(request, 200)
    assert order == ["commit"]
