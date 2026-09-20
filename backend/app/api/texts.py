"""Reading the pre-generated topic texts — §3.5.

A `GET` here never generates and never writes: it computes the current hash
the same way the job does, reports what the cache holds, and — only if
nothing is on its way — records a pre-generation job in the outbox.
"""

import inspect
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app import fallbacks, keys
from app.api.deps import get_current_student, get_llm, get_rule_deps, get_session
from app.apply import texts as apply_texts
from app.db.repo import sets as sets_repo
from app.db.repo import texts as texts_repo
from app.errors import NotFound
from app.events import dispatch, store
from app.events.dispatch import RuleDeps
from app.prompt_versions import text_versions
from app.schemas.auth import StudentCtx
from app.schemas.events import EventIn, EventType, TextOpenedPayload
from app.schemas.texts import GeneratedTextOut, TextOpenedIn

router = APIRouter(prefix="/texts", tags=["texts"])

TextKindQuery = Annotated[str, Query(pattern="^(guideline|explanation)$")]


async def _owned(session: AsyncSession, student_id: UUID, set_id: UUID):
    item = await sets_repo.get_set(session, student_id, set_id)
    if item is None:
        raise NotFound("set not found")
    return item


@router.get("/{set_id}/{skill_id}", response_model=GeneratedTextOut)
async def get_text(
    set_id: UUID,
    skill_id: str,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
    llm: Annotated[Any, Depends(get_llm)],
    kind: TextKindQuery = "guideline",
) -> GeneratedTextOut:
    item = await _owned(session, student.student_id, set_id)
    if not any(topic.skill_id == skill_id for topic in item.topics):
        raise NotFound("set topic not found")

    versions, model = text_versions()
    version = versions[kind]
    digest, _ = await apply_texts.current_hash(
        session, deps, student.student_id, set_id, skill_id, kind, version, model
    )
    owner = apply_texts.owner_of(kind, student.student_id)
    current = last = None
    if digest is not None:
        current, last = await texts_repo.get_current(
            session, owner, kind, skill_id, digest
        )
    # Ownership is checked above, before `last_ready` is looked up: a
    # guideline belongs to one student and must never leak through the stale
    # branch (T02).
    out = fallbacks.select_text(
        kind=kind,
        subject=skill_id,
        set_id=set_id,
        current_hash=digest,
        current=current,
        last_ready=last,
        llm_status=await _llm_status(llm),
    )
    if digest is not None and out.status in ("generating", "failed", "stale"):
        if current is None:
            await _ensure_job(session, deps, student.student_id, set_id, kind, digest)
    return out


async def _llm_status(llm: Any) -> str:
    """The shared status, read once per request; unknown reads as `ok`.

    Guessing `down` would mark every current text as saved for no reason.
    """
    if llm is None:
        return "ok"
    try:
        status = llm.status()
        return await status if inspect.isawaitable(status) else status
    except Exception:  # noqa: BLE001 — a status probe never fails a read
        return "ok"


async def _ensure_job(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    set_id: UUID,
    kind: str,
    digest: str,
) -> None:
    """Queue the set's pre-generation unless a job is already alive.

    `keys.text_job` has a 600-second TTL: if ARQ lost the job (a Redis
    flush, a crashed worker), the route is allowed to put it back (§16.3).
    """
    try:
        alive = await deps.redis.get(keys.text_job(kind, digest))
    except (RedisError, OSError):
        alive = None
    if alive:
        return
    versions, model = text_versions()
    job_id = await apply_texts.set_job_id(
        session, deps, student_id, set_id, versions, model
    )
    if job_id is None:
        return
    deps.jobs.enqueue(
        "bulk",
        "pregenerate_set",
        job_id=job_id,
        set_id=str(set_id),
        student_id=str(student_id),
    )


@router.post("/{set_id}/{skill_id}/opened", status_code=204)
async def mark_opened(
    set_id: UUID,
    skill_id: str,
    body: TextOpenedIn,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
) -> Response:
    """`guideline.opened` / `explanation.opened` — activity and
    `after_guideline` both read this event."""
    item = await _owned(session, student.student_id, set_id)
    if not any(topic.skill_id == skill_id for topic in item.topics):
        raise NotFound("set topic not found")
    versions, model = text_versions()
    digest, _ = await apply_texts.current_hash(
        session,
        deps,
        student.student_id,
        set_id,
        skill_id,
        body.kind,
        versions[body.kind],
        model,
    )
    event = await store.append(
        session,
        deps.redis,
        EventIn(
            type=(
                EventType.guideline_opened
                if body.kind == "guideline"
                else EventType.explanation_opened
            ),
            payload=TextOpenedPayload(
                set_id=set_id,
                skill_id=skill_id,
                kind=body.kind,
                text_hash=digest or "",
            ).model_dump(mode="json"),
            student_id=student.student_id,
            exam_id=item.exam_id,
            set_id=set_id,
            topic_skill_id=skill_id,
        ),
        dispatch_event=False,
    )
    await dispatch.dispatch(session, event, deps)
    return Response(status_code=204)


@router.post("/{set_id}/{skill_id}/regenerate", status_code=202)
async def regenerate(
    set_id: UUID,
    skill_id: str,
    student: Annotated[StudentCtx, Depends(get_current_student)],
    session: Annotated[AsyncSession, Depends(get_session)],
    deps: Annotated[RuleDeps, Depends(get_rule_deps)],
    kind: TextKindQuery = "guideline",
) -> dict[str, str]:
    """Force a regeneration — for a demo, and after a `failed` row."""
    item = await _owned(session, student.student_id, set_id)
    if not any(topic.skill_id == skill_id for topic in item.topics):
        raise NotFound("set topic not found")
    versions, model = text_versions()
    # Ручной перезапуск снимает защиту «три провала — больше не пробуем».
    for text_kind in ("guideline", "explanation"):
        digest, _ = await apply_texts.current_hash(
            session,
            deps,
            student.student_id,
            set_id,
            skill_id,
            text_kind,
            versions[text_kind],
            model,
        )
        if digest is not None:
            await texts_repo.reset_attempts(session, text_kind, digest)
    job_id = await apply_texts.set_job_id(
        session, deps, student.student_id, set_id, versions, model
    )
    if job_id is None:
        return {"status": "skipped"}
    deps.jobs.enqueue(
        "bulk",
        "pregenerate_set",
        job_id=job_id,
        set_id=str(set_id),
        student_id=str(student.student_id),
    )
    return {"status": "queued", "job_id": job_id}
