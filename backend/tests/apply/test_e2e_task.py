"""E2E: ответ на задачу → состояние → сет → прогноз.

Integration-тест, требует живые Postgres + Neo4j (фикстуры `db_session`,
`seeded_graph`, `templates_db`). Без них — skip.

Source: 20-B1-phase2.md §8, §10.1.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.apply.task_answered import apply_task_answered
from app.db.repo import tasks as tasks_repo
from app.events.dispatch import RuleDeps
from app.graph.queries import personal as personal_q
from app.schemas.events import Event, EventType, TaskAnsweredPayload
from app.schemas.tasks import (
    ParamSpec,
    TaskInstance,
    TaskTemplateSpec,
)
from app.tasks.generate import generate_instance

pytestmark = [pytest.mark.phase1, pytest.mark.integration]

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)

SKILL_ID = "math.alg.linear_eq"


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key, value, *, ex=None, nx=False):
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def incr(self, key) -> int:
        v = int(self.store.get(key, "0")) + 1
        self.store[key] = str(v)
        return v

    async def delete(self, key):
        self.store.pop(key, None)


def _template() -> TaskTemplateSpec:
    return TaskTemplateSpec(
        id="tpl.e2e.linear_eq",
        exam_id="SAT_MATH",
        type="mcq4",
        difficulty=3,
        skill_id=SKILL_ID,
        tags=[],
        time_reference_sec=60,
        kind="template",
        params={
            "a": ParamSpec(range=(2, 5)),
            "b": ParamSpec(range=(2, 9)),
            "c": ParamSpec(range=(10, 30)),
        },
        constraints=["(c - b) % a == 0", "c > b"],
        stem="{a}x + {b} = {c}",
        correct="(c - b)/a",
        distractors=[
            {"expr": "(c + b)/a", "misconception_id": None},
            {"expr": "c - b", "misconception_id": None},
            {"expr": "c / a", "misconception_id": None},
        ],
        solution=["{a}x = {c} - {b}", "x = {answer}"],
    )


@pytest.fixture
async def e2e_setup(db_session, seeded_graph, templates_db):
    """Template + instance в Postgres, ученик в графе, RuleDeps."""
    spec = _template()
    await tasks_repo.upsert_template(db_session, spec)
    await db_session.flush()

    student_id = uuid4()
    await personal_q.ensure_student(seeded_graph, student_id)

    inst = generate_instance(spec, seed=42, student_id=student_id)
    await tasks_repo.insert_instance(db_session, student_id, inst)
    await db_session.flush()

    deps = RuleDeps(
        graph=seeded_graph,
        redis=_FakeRedis(),
        params=__import__("app.config", fromlist=["KnowledgeParams"]).KnowledgeParams(),
        now=lambda: NOW,
    )
    return {
        "session": db_session,
        "driver": seeded_graph,
        "deps": deps,
        "student_id": student_id,
        "instance": inst,
    }


def _answer_event(student_id, instance: TaskInstance, key: str) -> Event:
    payload = TaskAnsweredPayload(
        instance_id=instance.id,
        answer=key,
        time_spent_sec=30,
        mode="topic",
        session_minute=5,
        after_guideline=False,
        hint_level_before=0,
    )
    return Event(
        id=1,
        type=EventType.task_answered,
        payload=payload.model_dump(mode="json"),
        student_id=student_id,
        session_id=None,
        exam_id=instance.exam_id,
        set_id=None,
        topic_skill_id=instance.skill_id,
        chat_id=None,
        occurred_at=NOW,
        extractor_version=None,
        source_event_ids=None,
        ingested_at=NOW,
        processed_at=None,
    )


async def test_answer_creates_state_and_evidence(e2e_setup):
    """Ответ → KnowledgeState + Evidence + bump версии."""
    s = e2e_setup
    inst = s["instance"]
    # Правильный ключ — options уже перемешаны, находим correct
    correct_key = next(o.key for o in inst.options if o.correct)
    event = _answer_event(s["student_id"], inst, correct_key)

    result = await apply_task_answered(s["session"], event, s["deps"])

    assert result.grade.correct is True
    assert result.state_after is not None
    assert result.state_after.skill_id == SKILL_ID
    assert result.knowledge_version >= 1
    assert result.solution == inst.solution_rendered

    # Evidence записан в графе
    evidence = await personal_q.list_evidence(s["driver"], s["student_id"], SKILL_ID)
    assert len(evidence) >= 1

    # Состояние есть в графе
    state = await personal_q.get_state(
        s["driver"], s["student_id"], SKILL_ID, inst.exam_id
    )
    assert state is not None
    assert state.n_correct >= 1


async def test_wrong_answer_marks_misconception_and_state(e2e_setup):
    """Неверный ответ → shaky-состояние, при попадании в дистрактор — misconception."""
    s = e2e_setup
    inst = s["instance"]
    wrong_key = next(
        (o.key for o in inst.options if not o.correct and o.misconception_id),
        None,
    )
    if wrong_key is None:
        pytest.skip("no misclassified distractor in this instance")

    event = _answer_event(s["student_id"], inst, wrong_key)
    result = await apply_task_answered(s["session"], event, s["deps"])

    assert result.grade.correct is False
    assert result.state_after is not None
    assert result.state_after.n_incorrect >= 1
