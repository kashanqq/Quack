"""Generated text cache keyed by kind and input hash (§3.4, §14.10).

`UNIQUE(kind, input_hash)` stays the cache key; `input_hash` already folds in
`student_id` and `subject`, so two students never collide. `(student_id,
kind, subject)` is the *lookup* used to find the last text that was ready for
this subject — that is what a stale read shows.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GeneratedText as GeneratedTextRow
from app.schemas.texts import GeneratedText

TextStatus = Literal["generating", "ready", "failed"]


def _to_schema(row: GeneratedTextRow) -> GeneratedText:
    return GeneratedText.model_validate(
        {name: getattr(row, name) for name in GeneratedText.model_fields}
    )


async def get_generated(
    session: AsyncSession, kind: str, input_hash: str
) -> GeneratedText | None:
    row = await _row(session, kind, input_hash)
    return _to_schema(row) if row is not None else None


async def _row(
    session: AsyncSession, kind: str, input_hash: str
) -> GeneratedTextRow | None:
    return await session.scalar(
        select(GeneratedTextRow).where(
            GeneratedTextRow.kind == kind, GeneratedTextRow.input_hash == input_hash
        )
    )


async def last_ready(
    session: AsyncSession, student_id: UUID | None, kind: str, subject: str
) -> GeneratedText | None:
    """The newest `ready` text for this subject — the stale fallback."""
    row = await session.scalar(
        select(GeneratedTextRow)
        .where(
            GeneratedTextRow.student_id.is_(None)
            if student_id is None
            else GeneratedTextRow.student_id == student_id,
            GeneratedTextRow.kind == kind,
            GeneratedTextRow.subject == subject,
            GeneratedTextRow.status == "ready",
        )
        .order_by(GeneratedTextRow.created_at.desc(), GeneratedTextRow.id.desc())
        .limit(1)
    )
    return _to_schema(row) if row is not None else None


async def get_current(
    session: AsyncSession,
    student_id: UUID | None,
    kind: str,
    subject: str,
    input_hash: str,
) -> tuple[GeneratedText | None, GeneratedText | None]:
    """(row for this exact hash, last ready row of the same subject)."""
    return (
        await get_generated(session, kind, input_hash),
        await last_ready(session, student_id, kind, subject),
    )


async def mark(
    session: AsyncSession,
    kind: str,
    input_hash: str,
    status: TextStatus,
    *,
    text: str | None = None,
    error: str | None = None,
    student_id: UUID | None = None,
    subject: str = "",
    set_id: UUID | None = None,
    model: str = "",
    prompt_version: str = "",
) -> GeneratedText:
    """Upsert one cache row; `attempts` grows on every non-ready write."""
    now = datetime.now(UTC)
    row = await _row(session, kind, input_hash)
    if row is None:
        row = GeneratedTextRow(
            id=uuid4(),
            kind=kind,
            input_hash=input_hash,
            text=text,
            model=model,
            prompt_version=prompt_version,
            created_at=now,
            student_id=student_id,
            subject=subject,
            set_id=set_id,
            status=status,
            attempts=0 if status == "ready" else 1,
            error=error,
            updated_at=now,
        )
        session.add(row)
    else:
        row.status = status
        row.updated_at = now
        row.error = error
        if text is not None:
            row.text = text
        if model:
            row.model = model
        if prompt_version:
            row.prompt_version = prompt_version
        if subject:
            row.subject = subject
        if set_id is not None:
            row.set_id = set_id
        if student_id is not None:
            row.student_id = student_id
        if status != "ready":
            row.attempts = (row.attempts or 0) + 1
    await session.flush()
    return _to_schema(row)


async def put_generated(
    session: AsyncSession,
    kind: str,
    input_hash: str,
    text: str,
    model: str,
    prompt_version: str,
) -> None:
    """Phase 1–3 shape kept: a plain ready text with no subject."""
    await mark(
        session,
        kind,
        input_hash,
        "ready",
        text=text,
        model=model,
        prompt_version=prompt_version,
    )


async def reset_attempts(session: AsyncSession, kind: str, input_hash: str) -> None:
    """Manual regeneration clears the «три провала подряд» guard (§3.6)."""
    row = await _row(session, kind, input_hash)
    if row is None:
        return
    row.attempts = 0
    row.error = None
    await session.flush()
