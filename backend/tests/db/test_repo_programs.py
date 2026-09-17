"""Saved program error and isolation behavior without a live database."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db.models import ProgramCache, SavedProgram
from app.db.repo.programs import list_saved, remove_saved, save_program
from app.errors import Conflict, NotFound


class ProgramSession:
    def __init__(self):
        self.program = None
        self.saved = {}
        self.query = None

    async def get(self, model, key):
        if model is ProgramCache:
            return self.program
        if model is SavedProgram:
            return self.saved.get(key)
        raise AssertionError(model)

    def add(self, row):
        self.saved[(row.student_id, row.program_id)] = row

    async def delete(self, row):
        self.saved.pop((row.student_id, row.program_id))

    async def flush(self):
        pass

    async def scalars(self, query):
        self.query = query
        return self

    def all(self):
        return list(self.saved.values())


@pytest.mark.asyncio
async def test_missing_duplicate_and_student_owned_saved_programs():
    session = ProgramSession()
    first_student, second_student = uuid4(), uuid4()
    with pytest.raises(NotFound):
        await save_program(session, first_student, "program-1")
    session.program = object()
    await save_program(session, first_student, "program-1")
    with pytest.raises(Conflict):
        await save_program(session, first_student, "program-1")
    assert await session.get(SavedProgram, (second_student, "program-1")) is None
    with pytest.raises(NotFound):
        await remove_saved(session, second_student, "program-1")
    await remove_saved(session, first_student, "program-1")
    with pytest.raises(NotFound):
        await remove_saved(session, first_student, "program-1")


@pytest.mark.asyncio
async def test_list_saved_query_filters_student_id():
    session = ProgramSession()
    student_id = uuid4()
    session.saved[(student_id, "program-1")] = SavedProgram(
        student_id=student_id,
        program_id="program-1",
        saved_at=datetime.now(UTC),
    )
    result = await list_saved(session, student_id)
    assert [item.program_id for item in result] == ["program-1"]
    compiled = session.query.compile()
    assert "saved_programs.student_id" in str(compiled)
    assert student_id in compiled.params.values()
