"""Set summaries — statistics written by the rule, text by the job (§4).

One row per set (`UNIQUE(set_id)`). The statistics land synchronously inside
the `set.completed` transaction, so the Overview always has numbers even if
the model never answers; the text is filled in later and may stay `None`.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SetSummary
from app.schemas.common import ExamId
from app.schemas.roadmap import SetSummaryOut
from app.schemas.sets import SetStats


def _to_schema(row: SetSummary) -> SetSummaryOut:
    return SetSummaryOut(
        set_id=row.set_id,
        exam_id=row.exam_id,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        text=row.text,
        stats=SetStats.model_validate(row.stats),
        prompt_version=row.prompt_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _row(session: AsyncSession, set_id: UUID) -> SetSummary | None:
    return await session.scalar(select(SetSummary).where(SetSummary.set_id == set_id))


async def upsert_stats(
    session: AsyncSession,
    student_id: UUID,
    set_id: UUID,
    exam_id: ExamId,
    stats: SetStats,
    *,
    input_hash: str,
    status: str = "generating",
) -> SetSummaryOut:
    """Write the frozen facts of a finished set.

    A replayed `set.completed` recomputes the statistics but never overwrites
    a text that is already `ready` (§4.5).
    """
    now = datetime.now(UTC)
    row = await _row(session, set_id)
    payload = stats.model_dump(mode="json")
    if row is None:
        row = SetSummary(
            id=uuid4(),
            student_id=student_id,
            set_id=set_id,
            text=None,
            stats=payload,
            created_at=now,
            exam_id=exam_id,
            status=status,
            input_hash=input_hash,
            updated_at=now,
        )
        session.add(row)
    elif row.status != "ready" or row.input_hash != input_hash:
        row.stats = payload
        row.exam_id = exam_id
        row.updated_at = now
        if row.status != "ready":
            row.status = status
            row.input_hash = input_hash
    await session.flush()
    return _to_schema(row)


async def set_text(
    session: AsyncSession,
    set_id: UUID,
    text: str | None,
    prompt_version: str | None,
    status: str,
) -> SetSummaryOut | None:
    row = await _row(session, set_id)
    if row is None:
        return None
    row.text = text
    row.prompt_version = prompt_version
    row.status = status
    row.updated_at = datetime.now(UTC)
    await session.flush()
    return _to_schema(row)


async def get(session: AsyncSession, set_id: UUID) -> SetSummaryOut | None:
    row = await _row(session, set_id)
    return _to_schema(row) if row is not None else None


async def get_latest(
    session: AsyncSession, student_id: UUID, exam_id: ExamId | None = None
) -> SetSummaryOut | None:
    """The student's newest summary, optionally narrowed to one exam (§0.2)."""
    statement = select(SetSummary).where(SetSummary.student_id == student_id)
    if exam_id is not None:
        statement = statement.where(SetSummary.exam_id == exam_id)
    row = await session.scalar(
        statement.order_by(SetSummary.created_at.desc(), SetSummary.id.desc()).limit(1)
    )
    return _to_schema(row) if row is not None else None


async def get_latest_text(
    session: AsyncSession, student_id: UUID, before_set_id: UUID | None = None
) -> str | None:
    """Text of the student's latest set summary other than `before_set_id`.

    Phase-3 signature, kept: the tutor context reads it directly.
    """
    statement = select(SetSummary.text).where(SetSummary.student_id == student_id)
    if before_set_id is not None:
        statement = statement.where(SetSummary.set_id != before_set_id)
    return await session.scalar(
        statement.where(SetSummary.text.is_not(None))
        .order_by(SetSummary.created_at.desc())
        .limit(1)
    )


async def get_previous(
    session: AsyncSession, student_id: UUID, before_set_id: UUID | None = None
) -> SetSummaryOut | None:
    """The newest summary other than this set's, whatever its status."""
    statement = select(SetSummary).where(SetSummary.student_id == student_id)
    if before_set_id is not None:
        statement = statement.where(SetSummary.set_id != before_set_id)
    row = await session.scalar(
        statement.order_by(SetSummary.created_at.desc(), SetSummary.id.desc()).limit(1)
    )
    return _to_schema(row) if row is not None else None
