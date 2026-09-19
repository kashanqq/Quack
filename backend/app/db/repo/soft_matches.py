"""Soft-match rows: (summary_hash, program_id, prompt_version) → score (§5.5)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SoftMatch
from app.schemas.matching import SoftMatchOut


def _to_schema(row: SoftMatch, *, stale: bool) -> SoftMatchOut:
    return SoftMatchOut(
        program_id=row.program_id,
        score=row.score if row.score is not None else 0.5,
        fit_text=row.text,
        caveat=row.caveat,
        matched_traits=list(row.matched_traits or []),
        confidence=row.confidence or "medium",  # type: ignore[arg-type]
        prompt_version=row.prompt_version,
        stale=stale,
    )


async def get_many(
    session: AsyncSession,
    summary_hash: str,
    program_ids: list[str],
    prompt_version: str,
) -> dict[str, SoftMatchOut]:
    """Current-version rows, falling back to an older prompt as `stale`."""
    if not program_ids:
        return {}
    rows = (
        await session.scalars(
            select(SoftMatch).where(
                SoftMatch.summary_hash == summary_hash,
                SoftMatch.program_id.in_(program_ids),
            )
        )
    ).all()
    out: dict[str, SoftMatchOut] = {}
    for row in rows:
        if row.prompt_version == prompt_version:
            out[row.program_id] = _to_schema(row, stale=False)
    for row in sorted(rows, key=lambda item: item.created_at):
        if row.program_id not in out:
            out[row.program_id] = _to_schema(row, stale=True)
    return out


async def put(
    session: AsyncSession,
    summary_hash: str,
    program_id: str,
    prompt_version: str,
    *,
    score: float | None,
    text: str | None,
    caveat: str | None = None,
    matched_traits: list[str] | None = None,
    confidence: str | None = None,
    model: str,
) -> None:
    row = await session.get(SoftMatch, (summary_hash, program_id, prompt_version))
    if row is None:
        session.add(
            SoftMatch(
                summary_hash=summary_hash,
                program_id=program_id,
                prompt_version=prompt_version,
                score=score,
                text=text,
                caveat=caveat,
                matched_traits=matched_traits or [],
                confidence=confidence,
                model=model,
            )
        )
    else:
        row.score = score
        row.text = text
        row.caveat = caveat
        row.matched_traits = matched_traits or []
        row.confidence = confidence
        row.model = model
    await session.flush()


async def delete_for_program(session: AsyncSession, program_id: str) -> int:
    """The program's `environment_text` changed — every judgement about it
    was made on the old text (§5.5)."""
    result = await session.execute(
        delete(SoftMatch).where(SoftMatch.program_id == program_id)
    )
    await session.flush()
    return int(result.rowcount or 0)
