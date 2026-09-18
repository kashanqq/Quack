"""Task instance lookup must scope the query to the owning student."""

from uuid import uuid4

import pytest

from app.db.repo.tasks import get_instance


class TaskSession:
    def __init__(self):
        self.query = None

    async def scalar(self, query):
        self.query = query
        return None


@pytest.mark.asyncio
async def test_foreign_task_instance_looks_missing():
    student_id, instance_id = uuid4(), uuid4()
    session = TaskSession()

    assert await get_instance(session, student_id, instance_id) is None
    compiled = session.query.compile()
    assert "task_instances.student_id" in str(compiled)
    assert "task_instances.id" in str(compiled)
    assert student_id in compiled.params.values()
    assert instance_id in compiled.params.values()
