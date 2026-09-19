"""Observer — one structured-output call over a window of the prep chat.

Source: docs/tz/phase3-agents.md §3.8, §5.1 C1, §5.2 F1;
memory-architecture §8.1.

The observer reads a window of unprocessed chat messages and turns what
happened into a list of observations; it never draws conclusions about
skill state itself — aggregation into evidence, skill states and forecasts
is done by the rule `apply.observation`. `run` writes nothing and filters
nothing: the event keeps exactly what the model said, the rule decides what
to apply (confidence threshold, reference checks).

The output schema lives in `app.schemas.observer` (the event payload is
validated by `events.store`, and `schemas` may not import `agents`); it is
re-exported here so phase-1 imports keep working.
"""

from __future__ import annotations

import time

import structlog

from app.config import settings
from app.llm.client import LLMLike
from app.llm.prompts import load_prompt
from app.schemas.llm import LLMMessage, ModelSlot
from app.schemas.observer import (
    Observation,
    ObservationKind,
    ObservationOut,
    ObserverContext,
    ObserverResult,
    ObserverWindow,
)

__all__ = [
    "Observation",
    "ObservationKind",
    "ObservationOut",
    "render_window",
    "run",
]

_logger = structlog.get_logger(__name__)

_MESSAGE_CHARS = 2000
_USER_TURN = "Верни наблюдения по окну выше."
_LEVEL_WORDS = {
    "low_data": "мало данных",
    "weak": "слабо",
    "shaky": "шатко",
    "solid": "уверенно",
    "closed": "закрыто",
}


def _clip(text: str) -> str:
    return text if len(text) <= _MESSAGE_CHARS else text[:_MESSAGE_CHARS] + "…"


def render_window(window: ObserverWindow) -> str:
    lines: list[str] = []
    for message in window.messages:
        if message.role == "user":
            lines.append(f"[event_id={message.event_id}] ученик: {_clip(message.text)}")
            continue
        markup = message.markup
        tags = []
        if markup is not None:
            if markup.mode:
                tags.append(f"mode={markup.mode}")
            if markup.hint_level is not None:
                tags.append(f"hint={markup.hint_level}")
            if markup.gave_task_instance_id is not None:
                tags.append(f"task={markup.gave_task_instance_id}")
        head = f"репетитор ({', '.join(tags)})" if tags else "репетитор"
        lines.append(f"[event_id={message.event_id}] {head}: {_clip(message.text)}")
    return "\n".join(lines) if lines else "нет"


def render_tasks(window: ObserverWindow) -> str:
    """Stem and options only — never the key or `answer_forms`."""
    if not window.tasks:
        return "нет"
    blocks: list[str] = []
    for task in window.tasks:
        lines = [
            f"instance_id={task.instance_id}, skill_id={task.skill_id}, "
            f"тип={task.type}, выдана в event_id={task.issued_event_id}",
            f"условие: {task.stem}",
        ]
        lines.extend(f"{option.key}: {option.text}" for option in task.options)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def render_skills(context: ObserverContext) -> str:
    if not context.skills:
        return "нет"
    return "\n".join(
        f"{s.id} — {s.name}: {s.description} ({_LEVEL_WORDS.get(s.level, s.level)})"
        for s in context.skills
    )


def render_misconceptions(context: ObserverContext) -> str:
    if not context.misconceptions:
        return "нет"
    return "\n".join(
        f"{m.id} — {m.name}: {m.description} "
        f"(статус у ученика: {m.status or 'нет'}; {m.scope})"
        for m in context.misconceptions
    )


async def run(
    client: LLMLike,
    window: ObserverWindow,
    context: ObserverContext,
    *,
    slot: ModelSlot,
) -> ObserverResult:
    """One `structured` call; `LLMUnavailable` and provider errors propagate
    — whether to retry is the job's decision."""
    started = time.perf_counter()
    prompt = load_prompt("observer")
    system = prompt.render(
        window=render_window(window),
        skills=render_skills(context),
        misconceptions=render_misconceptions(context),
        task_instance=render_tasks(window),
        previous_summary=context.previous_summary or "нет",
    )
    messages = [
        LLMMessage(role="system", content=system),
        LLMMessage(role="user", content=_USER_TURN),
    ]
    out = await client.structured(messages, ObservationOut, slot)
    _logger.info(
        "observer_run",
        chat_id=str(window.chat_id),
        window=len(window.messages),
        tasks=len(window.tasks),
        skills=len(context.skills),
        misconceptions=len(context.misconceptions),
        prompt_chars=len(system),
        observations=len(out.observations),
        ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return ObserverResult(
        out=out,
        extractor_version=prompt.extractor_version,
        model=settings.MODEL_BULK if slot == "bulk" else settings.MODEL_CHAT,
        raw_count=len(out.observations),
    )
