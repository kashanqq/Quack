"""Commit the request transaction before the answer leaves the building (§10).

A dependency with `yield` has its exit code run *after* the response has been
sent — FastAPI's documented behaviour since 0.106, and easy to verify with a
slow teardown and a real socket. So a `get_session` that commits in its
teardown tells the client "202, accepted" and only then tries to make that
true; if the commit fails, the client has already been told a lie.

Phase 5 (§10, §15 "PG write откатился") needs the opposite order: nothing is
acknowledged that is not durable. This module is called from the HTTP
middleware, right after the endpoint produced its response and before that
response is handed back to be sent:

    endpoint → **persist intents + commit** → send → session teardown

The durable job intents are written in that same transaction (§9.2), so a
`202` for a background job means its intent is on disk. Delivery to ARQ
happens straight after the commit: a failed delivery is recoverable from the
row, a failed commit is not something a client should hear about as success.

A failed request is never committed. The commit is skipped for any response
of 400 or above, and the rollback in `get_session` still runs when the
teardown comes — an error must not leave half a write behind.
"""

from __future__ import annotations

import structlog
from fastapi import Request

_logger = structlog.get_logger(__name__)

#: Where `get_session` parks the request's session for this module to find.
SESSION_ATTR = "db_session"


async def commit_request(request: Request, status_code: int) -> None:
    """Persist the recorded job intents, commit, then hand them to the queue.

    Raises whatever the commit raised: the caller turns that into `500
    internal`, which is the honest answer — the work did not land.
    """
    session = getattr(request.state, SESSION_ATTR, None)
    if session is None:
        return
    # Take it off the request: the teardown must not find it a second time,
    # and a retry of this function must not commit twice.
    setattr(request.state, SESSION_ATTR, None)
    if status_code >= 400:
        await session.rollback()
        return

    outbox = getattr(request.state, "job_outbox", None)
    try:
        if outbox is not None and outbox.entries:
            await outbox.persist(session)
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    if outbox is not None and outbox.ready:
        try:
            await outbox.deliver(
                getattr(request.app.state, "sessionmaker", None),
                getattr(request.app.state, "arq", None),
            )
        except Exception:  # noqa: BLE001 — `outbox_replay` picks the row back up
            _logger.warning("outbox_deliver_failed", exc_info=True)
