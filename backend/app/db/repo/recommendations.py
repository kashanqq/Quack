"""The Quack feed in Postgres — §8.4, §14.10.

`reason_hash` is the identity of a recommendation: the same cause produces
the same open row, a disappeared cause expires it, and a decline suppresses
that cause until its parameters change.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Recommendation as RecommendationRow
from app.schemas.quack import (
    BatchResult,
    RecDraft,
    RecommendationAction,
    RecommendationOut,
)

_OPEN = ("pending", "shown")
_CLOSED = ("accepted", "declined", "expired")


def _to_schema(row: RecommendationRow) -> RecommendationOut:
    payload = dict(row.payload or {})
    return RecommendationOut(
        id=row.id,
        kind=row.kind,  # type: ignore[arg-type]
        urgency=row.urgency,  # type: ignore[arg-type]
        position=row.position,
        status=row.status,  # type: ignore[arg-type]
        title=payload.get("title", ""),
        reason=payload.get("reason", ""),
        action_text=payload.get("action_text", ""),
        action=RecommendationAction.model_validate(
            payload.get("action") or {"kind": "acknowledge"}
        ),
        forecast_after=payload.get("forecast_after"),
        exam_id=row.exam_id,  # type: ignore[arg-type]
        program_id=payload.get("program_id"),
        milestone_key=payload.get("milestone_key"),
        reason_hash=row.reason_hash,
        created_at=row.created_at,
        shown_at=row.shown_at,
        decided_at=row.decided_at,
        expires_at=row.expires_at,
    )


def _payload(draft: RecDraft) -> dict:
    return {
        "title": draft.title,
        "reason": draft.reason,
        "action_text": draft.action_text,
        "action": draft.action.model_dump(mode="json"),
        "forecast_after": (
            draft.forecast_after.model_dump(mode="json")
            if draft.forecast_after is not None
            else None
        ),
        "program_id": draft.program_id,
        "milestone_key": draft.milestone_key,
    }


async def list_open(
    session: AsyncSession, student_id: UUID, *, now: datetime | None = None
) -> list[RecommendationOut]:
    """`pending` + `shown`, expired-by-date filtered out on read (§8.4)."""
    rows = (
        await session.scalars(
            select(RecommendationRow)
            .where(
                RecommendationRow.student_id == student_id,
                RecommendationRow.status.in_(_OPEN),
            )
            .order_by(RecommendationRow.position, RecommendationRow.created_at)
        )
    ).all()
    moment = now or datetime.now(UTC)
    return [
        _to_schema(row)
        for row in rows
        if row.expires_at is None or row.expires_at >= moment
    ]


async def get(
    session: AsyncSession, student_id: UUID, recommendation_id: UUID
) -> RecommendationOut | None:
    row = await _row(session, student_id, recommendation_id)
    return _to_schema(row) if row is not None else None


async def _row(
    session: AsyncSession, student_id: UUID, recommendation_id: UUID
) -> RecommendationRow | None:
    return await session.scalar(
        select(RecommendationRow).where(
            RecommendationRow.id == recommendation_id,
            RecommendationRow.student_id == student_id,
        )
    )


async def history(
    session: AsyncSession, student_id: UUID, limit: int = 50
) -> list[RecommendationOut]:
    rows = (
        await session.scalars(
            select(RecommendationRow)
            .where(
                RecommendationRow.student_id == student_id,
                RecommendationRow.status.in_(_CLOSED),
            )
            .order_by(
                RecommendationRow.decided_at.desc().nullslast(),
                RecommendationRow.created_at.desc(),
            )
            .limit(limit)
        )
    ).all()
    return [_to_schema(row) for row in rows]


async def declined_hashes(
    session: AsyncSession, student_id: UUID, window_days: int, *, now: datetime
) -> set[str]:
    """Causes the student rejected recently — they are not offered again."""
    since = now - timedelta(days=window_days)
    rows = await session.scalars(
        select(RecommendationRow.reason_hash).where(
            RecommendationRow.student_id == student_id,
            RecommendationRow.status == "declined",
            RecommendationRow.decided_at.is_not(None),
            RecommendationRow.decided_at >= since,
        )
    )
    return set(rows.all())


async def mark_shown(
    session: AsyncSession,
    student_id: UUID,
    recommendation_ids: list[UUID] | None,
    *,
    now: datetime,
) -> int:
    statement = (
        update(RecommendationRow)
        .where(
            RecommendationRow.student_id == student_id,
            RecommendationRow.status == "pending",
        )
        .values(status="shown", shown_at=now)
    )
    if recommendation_ids:
        statement = statement.where(RecommendationRow.id.in_(recommendation_ids))
    result = await session.execute(statement)
    await session.flush()
    return int(result.rowcount or 0)


async def decide(
    session: AsyncSession,
    student_id: UUID,
    recommendation_id: UUID,
    status: str,
    *,
    now: datetime,
    decision_event_id: int | None = None,
) -> RecommendationOut | None:
    row = await _row(session, student_id, recommendation_id)
    if row is None:
        return None
    row.status = status
    row.decided_at = now
    if decision_event_id is not None:
        row.decision_event_id = decision_event_id
    await session.flush()
    return _to_schema(row)


async def expire_siblings(
    session: AsyncSession,
    student_id: UUID,
    kind: str,
    exam_id: str | None,
    *,
    keep_id: UUID,
    now: datetime,
) -> int:
    """Accepting one pace variant retires the other variants of that exam."""
    statement = (
        update(RecommendationRow)
        .where(
            RecommendationRow.student_id == student_id,
            RecommendationRow.kind == kind,
            RecommendationRow.status.in_(_OPEN),
            RecommendationRow.id != keep_id,
        )
        .values(status="expired", decided_at=now)
    )
    if exam_id is not None:
        statement = statement.where(RecommendationRow.exam_id == exam_id)
    result = await session.execute(statement)
    await session.flush()
    return int(result.rowcount or 0)


async def reconcile(
    session: AsyncSession,
    student_id: UUID,
    drafts: list[RecDraft],
    *,
    urgent_only: bool,
    now: datetime,
    batch_id: UUID | None = None,
) -> BatchResult:
    """Bring the open feed in line with a freshly planned one (§8.2).

    An urgent-only run writes `urgent`/`high` drafts and expires causes that
    are gone; `normal`/`low` wait for the cron so Quack does not chatter.
    """
    open_rows = {
        row.reason_hash: row
        for row in (
            await session.scalars(
                select(RecommendationRow).where(
                    RecommendationRow.student_id == student_id,
                    RecommendationRow.status.in_(_OPEN),
                )
            )
        ).all()
    }
    written = [
        draft
        for draft in drafts
        if not urgent_only or draft.urgency in ("urgent", "high")
    ]
    created = updated = 0
    for draft in written:
        row = open_rows.get(draft.reason_hash)
        payload = _payload(draft)
        if row is None:
            session.add(
                RecommendationRow(
                    id=uuid4(),
                    student_id=student_id,
                    kind=draft.kind,
                    payload=payload,
                    status="pending",
                    created_at=now,
                    reason_hash=draft.reason_hash,
                    urgency=draft.urgency,
                    position=draft.position,
                    exam_id=draft.exam_id,
                    expires_at=draft.expires_at,
                    batch_id=batch_id,
                )
            )
            created += 1
        else:
            row.payload = payload
            row.kind = draft.kind
            row.urgency = draft.urgency
            row.position = draft.position
            row.exam_id = draft.exam_id
            row.expires_at = draft.expires_at
            updated += 1

    # Причина исчезла из плана — рекомендация больше не актуальна. При
    # urgent-запуске `normal`/`low` не считались заново, поэтому их не
    # экспайрим: их судьбу решает крон.
    planned = {draft.reason_hash for draft in drafts}
    expired = 0
    for reason_hash, row in open_rows.items():
        if reason_hash in planned:
            continue
        if urgent_only and row.urgency not in ("urgent", "high"):
            continue
        row.status = "expired"
        row.decided_at = now
        expired += 1

    await session.flush()
    return BatchResult(
        created=created, updated=updated, expired=expired, batch_id=batch_id
    )
