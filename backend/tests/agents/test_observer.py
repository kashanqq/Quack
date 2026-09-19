"""observer.run — prompt rendering and the structured call
(docs/tz/phase3-agents.md §3.8, §6.7)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.agents import observer
from app.errors import LLMUnavailable
from app.llm.fake import FakeLLMClient
from app.schemas.chat import AssistantMarkup
from app.schemas.observer import (
    MisconceptionForObserver,
    Observation,
    ObservationOut,
    ObserverContext,
    ObserverWindow,
    SkillForObserver,
    WindowMessage,
    WindowTask,
)
from app.schemas.tasks import OptionOut

pytestmark = pytest.mark.phase3

NOW = datetime(2026, 9, 18, 12, tzinfo=UTC)
INSTANCE = uuid4()


def _window() -> ObserverWindow:
    return ObserverWindow(
        chat_id=uuid4(),
        student_id=uuid4(),
        exam_id="SAT_MATH",
        set_id=uuid4(),
        topic_skill_id="math.alg.abs_value_eq",
        messages=[
            WindowMessage(
                event_id=4420, role="user", text="|x-3|=2, x=5", occurred_at=NOW
            ),
            WindowMessage(
                event_id=4421,
                role="assistant",
                text="А вторая ветвь?",
                markup=AssistantMarkup(mode="review", hint_level=2),
                occurred_at=NOW,
            ),
            WindowMessage(event_id=4422, role="user", text="x=1 тоже", occurred_at=NOW),
        ],
        tasks=[
            WindowTask(
                instance_id=INSTANCE,
                issued_event_id=4419,
                skill_id="math.alg.abs_value_eq",
                stem="Решите |x − 3| = 2",
                options=[
                    OptionOut(key="A", text="1 и 5"),
                    OptionOut(key="B", text="5"),
                ],
                type="mcq4",
            )
        ],
    )


def _context() -> ObserverContext:
    return ObserverContext(
        skills=[
            SkillForObserver(
                id="math.alg.abs_value_eq",
                name="модуль",
                description="уравнения с модулем",
                level="shaky",
            )
        ],
        misconceptions=[
            MisconceptionForObserver(
                id="lib.abs_single_branch",
                name="одна ветвь",
                description="теряет вторую ветвь",
                status=None,
                scope="library",
            )
        ],
    )


def _valid() -> ObservationOut:
    return ObservationOut(
        observations=[
            Observation(
                kind="solution_step",
                outcome="incorrect",
                skill_id="math.alg.abs_value_eq",
                misconception_id="lib.abs_single_branch",
                event_ids=[4420],
                confidence=0.9,
            )
        ]
    )


async def test_prompt_renders_window_with_event_ids():
    client = FakeLLMClient([_valid()])

    await observer.run(client, _window(), _context(), slot="bulk")

    system = client.calls[0].messages[0].content
    assert "[event_id=4420] ученик:" in system
    assert "[event_id=4421] репетитор (mode=review, hint=2)" in system
    assert str(INSTANCE) in system
    assert "answer_forms" not in system
    assert "correct" not in system.split("Экземпляр задачи")[-1].split("Резюме")[0]


async def test_structured_called_with_slot_and_schema():
    client = FakeLLMClient([_valid()])

    result = await observer.run(client, _window(), _context(), slot="bulk")

    assert client.calls[0].method == "structured"
    assert client.calls[0].slot == "bulk"
    assert result.raw_count == 1
    assert result.extractor_version == "observer_v1"


async def test_invalid_then_valid_uses_builtin_retry():
    client = FakeLLMClient(['{"observations": [{"kind": "solution_step"}]}', _valid()])

    result = await observer.run(client, _window(), _context(), slot="bulk")

    assert result.raw_count == 1
    assert len(client.calls) == 2
    assert len(client.calls[1].messages) == len(client.calls[0].messages) + 1


async def test_two_invalid_raise_llm_unavailable():
    client = FakeLLMClient(["bad", "bad"])

    with pytest.raises(LLMUnavailable, match="structured output failed"):
        await observer.run(client, _window(), _context(), slot="bulk")


async def test_observer_output_keeps_low_confidence():
    """`run` filters nothing: the event must store what the model said."""
    low = ObservationOut(
        observations=[
            Observation(
                kind="question",
                skill_id="math.alg.abs_value_eq",
                event_ids=[4422],
                confidence=0.2,
            )
        ]
    )
    result = await observer.run(
        FakeLLMClient([low]), _window(), _context(), slot="chat"
    )
    assert result.out.observations[0].confidence == 0.2
