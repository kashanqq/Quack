"""Inputs of the two per-topic texts, and the stale→regenerate trigger (§3).

I/O only: read the graph and Postgres, build the input models, hand them to
the job (or to the route, which only needs their hash). The wording itself
is B2's; what goes *into* the wording is a knowledge-model decision and
lives here.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from sqlalchemy.ext.asyncio import AsyncSession

from app.apply.targets import p_target_for
from app.db.repo import profiles as profiles_repo
from app.db.repo import sets as sets_repo
from app.db.repo import tasks as tasks_repo
from app.db.repo import texts as texts_repo
from app.events.dispatch import RuleDeps
from app.graph.queries import canonical as canonical_q
from app.graph.queries import personal as personal_q
from app.knowledge import words
from app.knowledge.misconceptions import visible_to
from app.knowledge.text_inputs import inputs_hash, set_inputs_hash
from app.prompt_versions import text_versions
from app.schemas.events import Event, EventType
from app.schemas.sets import SetOut, TopicOut
from app.schemas.texts import (
    ExamFormatHint,
    ExplanationInputs,
    GuidelineInputs,
    MisconceptionBrief,
    PrerequisiteBrief,
    ProfileBrief,
    SetBrief,
    SkillBrief,
)

_logger = structlog.get_logger(__name__)

_MAX_PREREQUISITES = 5
_MAX_TEMPLATE_TAGS = 8

# Какие тексты нужны топику каждого вида (§3.1).
TEXT_KINDS: dict[str, tuple[str, ...]] = {
    "topic": ("guideline", "explanation"),
    "review": ("guideline", "explanation"),
    "check": ("explanation",),
}


def p_target_words(p_target: float) -> str:
    """Words, not a number the student would read as a promise."""
    percent = int(round(p_target * 100 / 5.0) * 5)
    return f"держать на уровне около {percent} процентов"


def subject_of(kind: str, skill_id: str) -> str:
    return skill_id


def owner_of(kind: str, student_id: UUID) -> UUID | None:
    """Explanations are shared between students, guidelines are not (§3.1)."""
    return None if kind == "explanation" else student_id


async def collect_inputs(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    set_id: UUID,
    skill_id: str,
    kind: str,
) -> GuidelineInputs | ExplanationInputs | None:
    """Everything the prompt needs, or None when the graph cannot answer."""
    if deps.graph is None:
        return None
    set_out = await sets_repo.get_set(session, student_id, set_id)
    if set_out is None:
        return None
    topic = next((item for item in set_out.topics if item.skill_id == skill_id), None)
    if topic is None:
        return None
    try:
        return await _collect(session, deps, student_id, set_out, topic, skill_id, kind)
    except (ServiceUnavailable, SessionExpired):
        _logger.warning("collect_inputs_graph_unavailable", skill_id=skill_id)
        return None


async def _collect(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    set_out: SetOut,
    topic: TopicOut,
    skill_id: str,
    kind: str,
) -> GuidelineInputs | ExplanationInputs | None:
    graph = deps.graph
    skill_ref = await canonical_q.get_skill(graph, skill_id)
    if skill_ref is None:
        return None
    exam_format = await canonical_q.get_exam_format(graph, set_out.exam_id)
    hint = ExamFormatHint(
        task_types=(
            sorted(exam_format.sections[0].item_types)
            if exam_format is not None and exam_format.sections
            else []
        ),
        calculator=(
            bool(exam_format.sections[0].calculator)
            if exam_format is not None and exam_format.sections
            else False
        ),
    )
    areas = {
        area.id: area.name
        for area in await canonical_q.list_areas(graph, set_out.exam_id)
    }
    area_name = ""
    for weight in await canonical_q.list_exam_skills(graph, set_out.exam_id):
        if weight.skill.id == skill_id:
            area_name = areas.get(weight.area_id, "")
            break
    brief = SkillBrief(
        id=skill_ref.id,
        name=skill_ref.name,
        description=skill_ref.description,
        exam_id=set_out.exam_id,
        area_name=area_name,
    )

    prerequisites = (await canonical_q.get_prerequisites(graph, skill_id, depth=1))[
        :_MAX_PREREQUISITES
    ]
    profile = await profiles_repo.get_profile(session, student_id)

    if kind == "explanation":
        names: list[str] = []
        for prerequisite in prerequisites:
            ref = await canonical_q.get_skill(graph, prerequisite.skill_id)
            if ref is not None:
                names.append(ref.name)
        return ExplanationInputs(
            skill=brief,
            prerequisites=names,
            exam_format_hint=hint,
            explanation_depth=(
                profile.questionnaire.pace.explanation_depth.value or "normal"
            ),
        )

    p_target = await p_target_for(session, deps, student_id, set_out.exam_id)
    states = {
        state.skill_id: state
        for state in await personal_q.get_states(graph, student_id, set_out.exam_id)
    }
    prerequisite_briefs: list[PrerequisiteBrief] = []
    for prerequisite in prerequisites:
        ref = await canonical_q.get_skill(graph, prerequisite.skill_id)
        if ref is None:
            continue
        prerequisite_briefs.append(
            PrerequisiteBrief(
                id=ref.id,
                name=ref.name,
                level=words.skill_level(states.get(ref.id), p_target, deps.params),
            )
        )

    now = deps.now()
    misconceptions: list[MisconceptionBrief] = []
    for state in await personal_q.get_misc_states(graph, student_id, [skill_id]):
        if not visible_to(state, "tutor", deps.params, now):
            continue
        ref = await canonical_q.get_misconception(graph, state.misconception_id)
        triggers = state.triggers or {}
        trigger_words = triggers.get("words") or triggers.get("trigger_words")
        misconceptions.append(
            MisconceptionBrief(
                id=state.misconception_id,
                name=state.name,
                description=ref.description if ref is not None else state.name,
                trigger_words=str(trigger_words) if trigger_words else None,
            )
        )

    root_of: list[str] = []
    for edge in await personal_q.list_root_causes(
        graph, student_id, deps.params.root_window_days
    ):
        if edge.root_skill_id != skill_id:
            continue
        ref = await canonical_q.get_skill(graph, edge.from_skill_id)
        if ref is not None and ref.name not in root_of:
            root_of.append(ref.name)

    templates = await tasks_repo.list_templates_for_skills(session, [skill_id])
    tags: list[str] = []
    for template in templates.get(skill_id, []):
        for tag in getattr(template, "tags", []) or []:
            if tag not in tags:
                tags.append(tag)

    return GuidelineInputs(
        skill=brief,
        state_words=words.skill_level(states.get(skill_id), p_target, deps.params),
        p_target_words=p_target_words(p_target),
        prerequisites=prerequisite_briefs,
        active_misconceptions=misconceptions,
        root_of=root_of,
        set=SetBrief(
            deadline=set_out.deadline,
            position_in_set=topic.position,
            n_topics=len(set_out.topics),
            kind=set_out.kind,
        ),
        profile=ProfileBrief(
            explanation_depth=(
                profile.questionnaire.pace.explanation_depth.value or "normal"
            ),
            hint_level=profile.questionnaire.pace.hint_level.value or "normal",
        ),
        exam_format_hint=hint,
        template_tags=tags[:_MAX_TEMPLATE_TAGS],
        mode="review" if topic.kind == "review" else "topic",
    )


async def current_hash(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    set_id: UUID,
    skill_id: str,
    kind: str,
    prompt_version: str,
    model: str,
) -> tuple[str | None, GuidelineInputs | ExplanationInputs | None]:
    """The hash the reader compares against, plus the inputs behind it."""
    inputs = await collect_inputs(session, deps, student_id, set_id, skill_id, kind)
    if inputs is None:
        return None, None
    return (
        inputs_hash(
            kind,
            owner_of(kind, student_id),
            subject_of(kind, skill_id),
            inputs,
            prompt_version,
            model,
        ),
        inputs,
    )


async def set_job_id(
    session: AsyncSession,
    deps: RuleDeps,
    student_id: UUID,
    set_id: UUID,
    prompt_versions: dict[str, str],
    model: str,
) -> str | None:
    """`pregen:{set_id}:{inputs_hash[:12]}` — one run per version of a set."""
    set_out = await sets_repo.get_set(session, student_id, set_id)
    if set_out is None:
        return None
    hashes: list[str] = []
    for topic in set_out.topics:
        for kind in TEXT_KINDS.get(topic.kind, ()):
            value, _ = await current_hash(
                session,
                deps,
                student_id,
                set_id,
                topic.skill_id,
                kind,
                prompt_versions.get(kind, kind),
                model,
            )
            if value is not None:
                hashes.append(value)
    if not hashes:
        return None
    return f"pregen:{set_id}:{set_inputs_hash(hashes)[:12]}"


async def on_topic_opened(session: AsyncSession, event: Event, deps: RuleDeps) -> None:
    """A stale guideline is regenerated when the student walks into the topic.

    Not on every piece of evidence: that would burn the model budget on text
    nobody is reading (§3.6). Between triggers the saved version is shown,
    and it is honest — it was true when the topic was entered.
    """
    if event.type != EventType.topic_opened:
        return
    payload = event.payload or {}
    set_id = payload.get("set_id")
    skill_id = payload.get("skill_id")
    if not set_id or not skill_id:
        return
    versions, model = text_versions()
    stale = False
    for kind in ("guideline", "explanation"):
        value, _ = await current_hash(
            session,
            deps,
            event.student_id,
            UUID(str(set_id)),
            str(skill_id),
            kind,
            versions.get(kind, kind),
            model,
        )
        if value is None:
            continue
        row = await texts_repo.get_generated(session, kind, value)
        if row is None or row.status != "ready":
            stale = True
    if not stale:
        return
    job_id = await set_job_id(
        session, deps, event.student_id, UUID(str(set_id)), versions, model
    )
    if job_id is None:
        return
    deps.jobs.enqueue(
        "bulk",
        "pregenerate_set",
        job_id=job_id,
        set_id=str(set_id),
        student_id=str(event.student_id),
    )
