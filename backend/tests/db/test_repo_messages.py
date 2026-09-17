"""Chat history query stays scoped to one student and ordered by time."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.db.models import Message
from app.db.repo.messages import list_messages


class MessageSession:
    def __init__(self, rows):
        self.rows = rows
        self.query = None

    async def scalars(self, query):
        self.query = query
        return self

    def all(self):
        return self.rows


@pytest.mark.asyncio
async def test_message_history_is_chronological_and_student_scoped():
    student_id, chat_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    older = Message(
        id=uuid4(),
        student_id=student_id,
        chat_id=chat_id,
        role="user",
        text="first",
        markup=None,
        event_id=1,
        created_at=now,
    )
    newer = Message(
        id=uuid4(),
        student_id=student_id,
        chat_id=chat_id,
        role="assistant",
        text="second",
        markup=None,
        event_id=2,
        created_at=now + timedelta(seconds=1),
    )
    session = MessageSession([newer, older])
    result = await list_messages(session, student_id, chat_id)
    assert [item.text for item in result] == ["first", "second"]
    compiled = session.query.compile()
    assert "messages.student_id" in str(compiled)
    assert "messages.chat_id" in str(compiled)
    assert student_id in compiled.params.values()
    assert chat_id in compiled.params.values()
