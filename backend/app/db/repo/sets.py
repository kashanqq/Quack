"""Postgres persistence for student-owned preparation sets."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Literal
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Set as SetRow
from app.db.models import SetTopic as TopicRow
from app.db.models import TaskInstance as InstanceRow
from app.errors import NotFound
from app.schemas.common import ExamId, SetStatus
from app.schemas.sets import SetOut, SetProgress, TopicOut

if TYPE_CHECKING:
    from app.sets.assemble import SetPlan


async def _owned_set(session: AsyncSession, student_id: UUID, set_id: UUID) -> SetRow:
    row = await session.scalar(
        select(SetRow).where(SetRow.id == set_id, SetRow.student_id == student_id)
    )
    if row is None:
        raise NotFound("set not found")
    return row


async def _topics(session: AsyncSession, set_id: UUID) -> list[TopicRow]:
    return list(
        (
            await session.scalars(
                select(TopicRow)
                .where(TopicRow.set_id == set_id)
                .order_by(TopicRow.position, TopicRow.skill_id)
            )
        ).all()
    )


async def _project(session: AsyncSession, row: SetRow) -> SetOut:
    topics = await _topics(session, row.id)
    # Knowledge labels and levels live in Neo4j, outside this Postgres repository.
    # Use explicit no-data values until the caller enriches the read model.
    return SetOut(
        id=row.id,
        exam_id=row.exam_id,
        area_ids=[],
        status=row.status,
        kind=row.kind,
        position=row.position,
        deadline=row.deadline,
        reason=row.reason,
        topics=[
            TopicOut(
                skill_id=topic.skill_id,
                name=topic.skill_id,
                kind=topic.kind,
                position=topic.position,
                status=topic.status,
                level="low_data",
                is_root=False,
                misconception_labels=[],
                subtitle=None,
            )
            for topic in topics
        ],
        progress=await count_progress(session, row.student_id, row.id),
        opened_at=row.opened_at,
        completed_at=row.completed_at,
    )


async def list_sets(
    session: AsyncSession, student_id: UUID, exam_id: ExamId
) -> list[SetOut]:
    rows = (
        await session.scalars(
            select(SetRow)
            .where(SetRow.student_id == student_id, SetRow.exam_id == exam_id)
            .order_by(SetRow.position, SetRow.created_at, SetRow.id)
        )
    ).all()
    return [await _project(session, row) for row in rows]


async def get_set(
    session: AsyncSession, student_id: UUID, set_id: UUID
) -> SetOut | None:
    row = await session.scalar(
        select(SetRow).where(SetRow.id == set_id, SetRow.student_id == student_id)
    )
    return await _project(session, row) if row is not None else None


def _planned_topics(plan: SetPlan) -> list[tuple[str, str]]:
    ordered: dict[str, str] = {}
    for kind, skills in (
        ("topic", plan.skill_ids),
        ("check", plan.checks),
        ("review", plan.reviews),
    ):
        for skill_id in skills:
            ordered.setdefault(skill_id, kind)
    return list(ordered.items())


async def _replace_topics(
    session: AsyncSession, set_id: UUID, plan: SetPlan, preserve_closed: bool
) -> None:
    old = await _topics(session, set_id)
    closed = {topic.skill_id for topic in old if topic.status == "closed"}
    await session.execute(delete(TopicRow).where(TopicRow.set_id == set_id))
    for position, (skill_id, kind) in enumerate(_planned_topics(plan)):
        session.add(
            TopicRow(
                set_id=set_id,
                skill_id=skill_id,
                position=position,
                kind=kind,
                status="closed" if preserve_closed and skill_id in closed else "open",
            )
        )
    await session.flush()


async def replace_plan(
    session: AsyncSession,
    student_id: UUID,
    exam_id: ExamId,
    plans: list[SetPlan],
    keep_current: bool,
) -> list[SetOut]:
    """Preserve completed work, optionally retain current, rebuild upcoming."""
    rows = (
        await session.scalars(
            select(SetRow)
            .where(SetRow.student_id == student_id, SetRow.exam_id == exam_id)
            .with_for_update()
        )
    ).all()
    current = next((row for row in rows if row.status == "current"), None)
    for row in rows:
        if row.status == "upcoming" or (row is current and not keep_current):
            await session.execute(delete(TopicRow).where(TopicRow.set_id == row.id))
            await session.delete(row)
    await session.flush()

    current_plan_index: int | None = None
    if keep_current and current is not None:
        current_skills = {
            topic.skill_id for topic in await _topics(session, current.id)
        }
        current_plan_index = next(
            (
                index
                for index, plan in enumerate(plans)
                if current_skills & {skill for skill, _ in _planned_topics(plan)}
            ),
            None,
        )
        if current_plan_index is None:
            # B1 assemble_sets omits current skills from its returned plans.
            current.position = 0

    position_offset = int(
        current is not None and keep_current and current_plan_index is None
    )
    now = datetime.now(UTC)
    for position, plan in enumerate(plans):
        if position == current_plan_index and current is not None:
            current.position = position
            current.deadline = plan.deadline
            current.reason = plan.reason
            current.rebuilt_at = now
            await _replace_topics(session, current.id, plan, preserve_closed=True)
            continue
        row = SetRow(
            id=uuid4(),
            student_id=student_id,
            exam_id=exam_id,
            status="upcoming",
            position=position + position_offset,
            deadline=plan.deadline,
            reason=plan.reason,
            kind=plan.kind,
            rebuilt_at=now,
        )
        session.add(row)
        await session.flush()
        await _replace_topics(session, row.id, plan, preserve_closed=False)
    await session.flush()
    return await list_sets(session, student_id, exam_id)


async def set_status(
    session: AsyncSession, student_id: UUID, set_id: UUID, status: SetStatus
) -> None:
    row = await _owned_set(session, student_id, set_id)
    row.status = status
    now = datetime.now(UTC)
    if status == "current" and row.opened_at is None:
        row.opened_at = now
    if status == "done" and row.completed_at is None:
        row.completed_at = now
    await session.flush()


async def set_topic_status(
    session: AsyncSession,
    set_id: UUID,
    skill_id: str,
    status: Literal["open", "closed"],
) -> None:
    row = await session.get(TopicRow, (set_id, skill_id))
    if row is None:
        raise NotFound("set topic not found")
    row.status = status
    await session.flush()


async def update_set(
    session: AsyncSession,
    student_id: UUID,
    set_id: UUID,
    skill_ids: list[str] | None,
    deadline: date | None,
) -> None:
    row = await _owned_set(session, student_id, set_id)
    if deadline is not None:
        row.deadline = deadline
    if skill_ids is not None:
        old = {topic.skill_id: topic for topic in await _topics(session, set_id)}
        await session.execute(delete(TopicRow).where(TopicRow.set_id == set_id))
        for position, skill_id in enumerate(dict.fromkeys(skill_ids)):
            previous = old.get(skill_id)
            session.add(
                TopicRow(
                    set_id=set_id,
                    skill_id=skill_id,
                    position=position,
                    kind=previous.kind if previous else "topic",
                    status=previous.status if previous else "open",
                )
            )
    await session.flush()


async def count_progress(
    session: AsyncSession, student_id: UUID, set_id: UUID
) -> SetProgress:
    await _owned_set(session, student_id, set_id)
    topics_total, topics_closed = (
        await session.execute(
            select(
                func.count(TopicRow.skill_id),
                func.count(TopicRow.skill_id).filter(TopicRow.status == "closed"),
            ).where(TopicRow.set_id == set_id)
        )
    ).one()
    skill_ids = select(TopicRow.skill_id).where(TopicRow.set_id == set_id)
    answered, correct = (
        await session.execute(
            select(
                func.count(InstanceRow.id),
                func.count(InstanceRow.id).filter(InstanceRow.correct.is_(True)),
            ).where(
                InstanceRow.student_id == student_id,
                InstanceRow.skill_id.in_(skill_ids),
                InstanceRow.mode.in_(("topic", "mock_topic", "mock_set")),
                InstanceRow.answered_at.is_not(None),
            )
        )
    ).one()
    return SetProgress(
        topics_closed=topics_closed,
        topics_total=topics_total,
        tasks_answered=answered,
        tasks_correct=correct,
    )
