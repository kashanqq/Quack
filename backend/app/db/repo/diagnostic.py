"""Student-scoped diagnostic run persistence.

The frozen Phase 2 contract lists names, but not full argument lists. Public
signatures remain unchanged; expected values can be passed positionally or by
keyword until the shared contract specifies them.
"""

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DiagnosticRun
from app.errors import Conflict, NotFound
from app.schemas.diagnostic import DiagnosticResult, DiagnosticState


def _value(args: tuple[Any, ...], kwargs: dict[str, Any], index: int, name: str) -> Any:
    if index < len(args):
        if name in kwargs:
            raise TypeError(f"{name} provided twice")
        return args[index]
    if name not in kwargs:
        raise TypeError(f"missing {name}")
    return kwargs[name]


def _json(value: Any, model: type[BaseModel]) -> dict[str, Any]:
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    return model.model_validate(value).model_dump(mode="json")


async def _owned_run(
    session: AsyncSession, student_id: UUID, run_id: UUID
) -> DiagnosticRun:
    row = await session.scalar(
        select(DiagnosticRun).where(
            DiagnosticRun.id == run_id,
            DiagnosticRun.student_id == student_id,
        )
    )
    if row is None:
        raise NotFound("diagnostic run not found")
    return row


async def create_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    student_id = _value(args, kwargs, 0, "student_id")
    exam_id = _value(args, kwargs, 1, "exam_id")
    state = _value(args, kwargs, 2, "state")
    active = await get_active_run(session, student_id, exam_id)
    if active is not None:
        raise Conflict("active diagnostic already exists")
    row = DiagnosticRun(
        id=kwargs.get("run_id", uuid4()),
        student_id=student_id,
        exam_id=exam_id,
        status="active",
        state=_json(state, DiagnosticState),
        result=None,
    )
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError as exc:
        raise Conflict("active diagnostic already exists") from exc
    return row


async def get_active_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    student_id = _value(args, kwargs, 0, "student_id")
    exam_id = _value(args, kwargs, 1, "exam_id")
    return await session.scalar(
        select(DiagnosticRun).where(
            DiagnosticRun.student_id == student_id,
            DiagnosticRun.exam_id == exam_id,
            DiagnosticRun.status == "active",
        )
    )


async def save_state(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    student_id = _value(args, kwargs, 0, "student_id")
    run_id = _value(args, kwargs, 1, "run_id")
    state = _value(args, kwargs, 2, "state")
    row = await _owned_run(session, student_id, run_id)
    if row.status != "active":
        raise Conflict("diagnostic run is not active")
    row.state = _json(state, DiagnosticState)
    await session.flush()
    return row


async def complete_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    student_id = _value(args, kwargs, 0, "student_id")
    run_id = _value(args, kwargs, 1, "run_id")
    result = _value(args, kwargs, 2, "result")
    row = await _owned_run(session, student_id, run_id)
    if row.status != "active":
        raise Conflict("diagnostic run is not active")
    row.result = _json(result, DiagnosticResult)
    row.status = "completed"
    row.completed_at = datetime.now(UTC)
    await session.flush()
    return row
