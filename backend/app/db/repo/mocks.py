"""Mock run persistence; answered progress lives on task instances."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MockRun
from app.db.models import TaskInstance as InstanceRow
from app.errors import Conflict, NotFound
from app.schemas.mocks import MockStartIn


def _value(args: tuple[Any, ...], kwargs: dict[str, Any], index: int, name: str) -> Any:
    if index < len(args):
        if name in kwargs:
            raise TypeError(f"{name} provided twice")
        return args[index]
    if name not in kwargs:
        raise TypeError(f"missing {name}")
    return kwargs[name]


async def create_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    student_id = _value(args, kwargs, 0, "student_id")
    exam_id = _value(args, kwargs, 1, "exam_id")
    kind = _value(args, kwargs, 2, "kind")
    section_name = _value(args, kwargs, 3, "section_name")
    instance_ids = _value(args, kwargs, 4, "instance_ids")
    request = MockStartIn(
        kind=kind,
        exam_id=exam_id,
        set_id=kwargs.get("set_id"),
        skill_id=kwargs.get("skill_id"),
        misconception_id=kwargs.get("misconception_id"),
    )
    unique_ids = list(dict.fromkeys(instance_ids))
    if unique_ids:
        owned = await session.scalar(
            select(func.count(InstanceRow.id)).where(
                InstanceRow.id.in_(unique_ids),
                InstanceRow.student_id == student_id,
            )
        )
        if owned != len(unique_ids):
            raise NotFound("task instance not found")
    row = MockRun(
        id=kwargs.get("run_id", uuid4()),
        student_id=student_id,
        exam_id=request.exam_id,
        kind=request.kind,
        set_id=request.set_id,
        skill_id=request.skill_id,
        misconception_id=request.misconception_id,
        section_name=section_name,
        instance_ids=unique_ids,
        predicted_before=kwargs.get("predicted_before"),
        status="active",
    )
    session.add(row)
    await session.flush()
    return row


async def get_run(session: AsyncSession, *args: Any, **kwargs: Any) -> Any:
    student_id = _value(args, kwargs, 0, "student_id")
    run_id = _value(args, kwargs, 1, "run_id")
    return await session.scalar(
        select(MockRun).where(
            MockRun.id == run_id,
            MockRun.student_id == student_id,
        )
    )


async def save_progress(
    session: AsyncSession, run_id: UUID, answered_instance_ids: list[UUID]
) -> None:
    row = await session.get(MockRun, run_id)
    if row is None:
        raise NotFound("mock run not found")
    if row.status != "active":
        raise Conflict("mock run is not active")
    selected = set(answered_instance_ids)
    if not selected.issubset(set(row.instance_ids)):
        raise NotFound("task instance not in mock run")
    if selected:
        owned = await session.scalar(
            select(func.count(InstanceRow.id)).where(
                InstanceRow.id.in_(selected),
                InstanceRow.student_id == row.student_id,
            )
        )
        if owned != len(selected):
            raise NotFound("task instance not in mock run")
        await session.execute(
            update(InstanceRow)
            .where(
                InstanceRow.id.in_(selected),
                InstanceRow.student_id == row.student_id,
                InstanceRow.answered_at.is_(None),
            )
            .values(answered_at=datetime.now(UTC))
        )
    await session.flush()


async def complete_run(
    session: AsyncSession, run_id: UUID, raw: float, scaled: float | None
) -> None:
    row = await session.get(MockRun, run_id)
    if row is None:
        raise NotFound("mock run not found")
    if row.status != "active":
        raise Conflict("mock run is not active")
    row.raw_score = raw
    row.scaled_score = scaled
    row.status = "completed"
    row.completed_at = datetime.now(UTC)
    await session.flush()
