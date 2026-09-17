"""Generated text cache keyed by kind and input hash."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GeneratedText as GeneratedTextRow
from app.schemas.texts import GeneratedText


def _to_schema(row: GeneratedTextRow) -> GeneratedText:
    return GeneratedText.model_validate(
        {name: getattr(row, name) for name in GeneratedText.model_fields}
    )


async def get_generated(
    session: AsyncSession, kind: str, input_hash: str
) -> GeneratedText | None:
    row = await session.scalar(
        select(GeneratedTextRow).where(
            GeneratedTextRow.kind == kind, GeneratedTextRow.input_hash == input_hash
        )
    )
    return _to_schema(row) if row is not None else None


async def put_generated(
    session: AsyncSession,
    kind: str,
    input_hash: str,
    text: str,
    model: str,
    prompt_version: str,
) -> None:
    row = await session.scalar(
        select(GeneratedTextRow).where(
            GeneratedTextRow.kind == kind, GeneratedTextRow.input_hash == input_hash
        )
    )
    if row is None:
        session.add(
            GeneratedTextRow(
                id=uuid4(),
                kind=kind,
                input_hash=input_hash,
                text=text,
                model=model,
                prompt_version=prompt_version,
                created_at=datetime.now(UTC),
            )
        )
    else:
        row.text = text
        row.model = model
        row.prompt_version = prompt_version
    await session.flush()
