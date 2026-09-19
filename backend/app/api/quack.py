"""Quack — the feed, the pace and the activity calendar (§8.5).

Reads are reads: the feed comes from `recommendations`, the calendar from
`daily_aggregates`, and only the pace is computed here (cached arithmetic,
§10.1). Accepting a recommendation writes an event and lets the phase-2
rules do the work.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_student, get_rule_deps, get_session
from app.apply import pace as apply_pace
from app.apply import quack as apply_quack
from app.db.repo import aggregates as aggregates_repo
from app.db.repo import profiles as profiles_repo
from app.db.repo import recommendations as recs_repo
from app.errors import NotFound, ValidationFailed
from app.events import dispatch, store, version
from app.events.dispatch import RuleDeps
from app.schemas.auth import StudentCtx
from app.schemas.common import Page
from app.schemas.events import (
    EventIn,
    EventType,
    RecommendationAcceptedPayload,
    RecommendationDeclinedPayload,
)
from app.schemas.quack import (
    ActivityOut,
    PaceOut,
    QuackOut,
    QuackSeenIn,
    RecDecisionIn,
    RecommendationOut,
)

router = APIRouter(prefix="/quack", tags=["quack"])


async def _activity(
    session: AsyncSession, deps: RuleDeps, student_id: UUID, days: int
) -> ActivityOut:
    profile = await profiles_repo.get_profile(session, student_id)
    return await aggregates_repo.activity(
        session,
        student_id,
        today=deps.now().date(),
        days=days,
        tz=deps.params.activity_tz,
        hours_declared=profile.questionnaire.pace.hours_per_week.value,
    )


@router.get("", response_model=QuackOut)
async def get_quack(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> QuackOut:
    pace = await apply_pace.compute_all(session, deps, student.student_id)
    items = await recs_repo.list_open(session, student.student_id, now=deps.now())
    batch = await apply_quack.batch_state(deps, student.student_id)
    pending = [item for item in items if item.status == "pending"]
    batch_at = batch.get("at")
    return QuackOut(
        pace=pace,
        items=sorted(items, key=lambda item: item.position),
        activity=await _activity(
            session, deps, student.student_id, deps.params.aggregate_window_days
        ),
        new_batch=bool(pending),
        batch_at=datetime.fromisoformat(batch_at) if batch_at else None,
        n_new=len(pending),
    )


@router.get("/pace", response_model=PaceOut)
async def get_pace(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> PaceOut:
    return await apply_pace.compute_all(session, deps, student.student_id)


@router.get("/activity", response_model=ActivityOut)
async def get_activity(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
    days: Annotated[int, Query(ge=1)] = 14,
) -> ActivityOut:
    if days > deps.params.aggregate_window_days:
        raise ValidationFailed(
            f"days must be at most {deps.params.aggregate_window_days}"
        )
    return await _activity(session, deps, student.student_id, days)


@router.get("/history", response_model=Page[RecommendationOut])
async def get_history(
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> Page[RecommendationOut]:
    items = await recs_repo.history(session, student.student_id, limit)
    return Page[RecommendationOut](items=items, total=len(items))


@router.post("/seen")
async def mark_seen(
    body: QuackSeenIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> dict[str, int]:
    """Opening Quack is not activity (activity is tasks, mocks and chat —
    product-logic §3.6), so no event is written. It does refresh the
    aggregates, at most once an hour per student (§9.5)."""
    shown = await recs_repo.mark_shown(
        session, student.student_id, body.recommendation_ids, now=deps.now()
    )
    hour = deps.now().strftime("%Y-%m-%dT%H")
    deps.jobs.enqueue(
        "bulk",
        "daily_aggregates",
        job_id=f"aggr:{student.student_id}:{hour}",
        student_id=str(student.student_id),
    )
    return {"shown": shown}


@router.post("/{recommendation_id}/accept", response_model=RecommendationOut)
async def accept(
    recommendation_id: UUID,
    response: Response,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> RecommendationOut:
    row = await recs_repo.get(session, student.student_id, recommendation_id)
    if row is None:
        raise NotFound("recommendation not found")
    if row.status == "accepted":
        # Идемпотентно: второй раз то же действие не выполняется.
        return row
    event = await store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.recommendation_accepted,
            payload=RecommendationAcceptedPayload(
                recommendation_id=recommendation_id,
                reason_hash=row.reason_hash,
                kind=row.kind,
                action=row.action,
            ).model_dump(mode="json"),
            student_id=student.student_id,
            exam_id=row.exam_id,
        ),
        dispatch_event=False,
    )
    results = await dispatch.dispatch(session, event, deps)
    # Правила могли пересобрать сеты — фронт обязан перечитать модель знаний.
    response.headers["X-Knowledge-Version"] = str(
        await version.get(deps.redis, student.student_id)
    )
    updated = results.get("apply_accept")
    if isinstance(updated, RecommendationOut):
        return updated
    refreshed = await recs_repo.get(session, student.student_id, recommendation_id)
    return refreshed or row


@router.post("/{recommendation_id}/decline", response_model=RecommendationOut)
async def decline(
    recommendation_id: UUID,
    body: RecDecisionIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> RecommendationOut:
    row = await recs_repo.get(session, student.student_id, recommendation_id)
    if row is None:
        raise NotFound("recommendation not found")
    if row.status == "declined":
        return row
    event = await store.append(
        session,
        deps.redis,
        EventIn(
            type=EventType.recommendation_declined,
            payload=RecommendationDeclinedPayload(
                recommendation_id=recommendation_id,
                reason_hash=row.reason_hash,
                kind=row.kind,
                reason=body.reason,
            ).model_dump(mode="json"),
            student_id=student.student_id,
            exam_id=row.exam_id,
        ),
        dispatch_event=False,
    )
    results = await dispatch.dispatch(session, event, deps)
    updated = results.get("log_decline")
    if isinstance(updated, RecommendationOut):
        return updated
    refreshed = await recs_repo.get(session, student.student_id, recommendation_id)
    return refreshed or row
