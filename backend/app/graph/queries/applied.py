"""`AppliedEvent` — the per-handler witness that a graph projection finished.

Phase 5, D02. Every personal write already has an idempotent key: `Evidence`
is `(event_id, skill_id, ordinal)` and `KnowledgeState` is keyed by
`(source_event_id, ordinal)`, so re-running a handler over the same event
changes nothing. What was missing is a way to *know* it finished: a crash
between the evidence and the state leaves the graph half-projected, and
nothing distinguishes that from a completed apply.

The marker is written **after** the handler's graph writes, in its own write
transaction. That ordering is what makes it safe, and it is deliberate:

- marker present ⇒ every write before it committed, so the graph part can be
  skipped and only the Postgres read-model needs rebuilding;
- marker absent ⇒ re-run the handler, which is a no-op for whatever already
  landed and repairs whatever did not.

A marker written *first*, or one written in the same transaction as only
*part* of the writes, would not have the first property. This is not a new
business entity: it stores no knowledge, only `(student_id, event_id,
handler, applied_at)`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from neo4j import AsyncDriver

from app.graph import labels as L

APPLIED_EVENT = L.APPLIED_EVENT


def marker_key(student_id: UUID, event_id: int, handler: str) -> str:
    """The single unique property of one marker (see `schema.cypher`)."""
    return f"{student_id}|{int(event_id)}|{handler}"


_MARK = f"""
MATCH (st:{L.STUDENT} {{id: $student_id}})
MERGE (a:{APPLIED_EVENT} {{key: $key}})
ON CREATE SET a.student_id = $student_id, a.event_id = $event_id,
              a.handler = $handler, a.applied_at = datetime($now),
              a.created = true
ON MATCH SET a.created = false
RETURN a.created AS created
"""

_CHECK = f"""
MATCH (a:{APPLIED_EVENT} {{key: $key}})
RETURN count(a) AS n
"""

_CHECK_MANY = f"""
MATCH (a:{APPLIED_EVENT} {{student_id: $student_id, handler: $handler}})
WHERE a.event_id IN $event_ids
RETURN collect(a.event_id) AS ids
"""


async def mark_applied(
    driver: AsyncDriver, student_id: UUID, event_id: int, handler: str
) -> bool:
    """Record that `handler` finished projecting `event_id`. `True` if new.

    The `MERGE` itself takes the lock on the marker node, so two workers
    racing on the same event serialize here instead of both deciding they are
    the first (§9.3).
    """

    async def work(tx) -> bool:
        result = await tx.run(
            _MARK,
            key=marker_key(student_id, event_id, handler),
            student_id=str(student_id),
            event_id=int(event_id),
            handler=handler,
            now=datetime.now(UTC).isoformat(),
        )
        record = await result.single()
        if record is None:
            raise LookupError(f"student {student_id} not in graph")
        return bool(record["created"])

    async with driver.session() as session:
        return await session.execute_write(work)


async def is_applied(
    driver: AsyncDriver, student_id: UUID, event_id: int, handler: str
) -> bool:
    async with driver.session() as session:
        result = await session.run(
            _CHECK, key=marker_key(student_id, event_id, handler)
        )
        record = await result.single()
    return bool(record is not None and int(record["n"]) > 0)


async def applied_ids(
    driver: AsyncDriver, student_id: UUID, event_ids: list[int], handler: str
) -> set[int]:
    """Which of these events this handler has already finished."""
    if not event_ids:
        return set()
    async with driver.session() as session:
        result = await session.run(
            _CHECK_MANY,
            student_id=str(student_id),
            event_ids=[int(value) for value in event_ids],
            handler=handler,
        )
        record = await result.single()
    return {int(value) for value in (record["ids"] if record else [])}
