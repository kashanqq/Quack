"""SELECTION_TOOLS / TUTOR_TOOLS registries (docs/tz/30-B2.md §5.2-§5.3, §6,
tests/agents/test_registries.py)."""

from __future__ import annotations

import pytest

from app.agents.selection import SELECTION_TOOLS, UpdateProfileArgs, save_program
from app.agents.tutor import TUTOR_TOOLS
from app.llm.tools import ToolCtx

pytestmark = pytest.mark.phase1

_SELECTION_TOOL_NAMES = {
    "update_profile",
    "run_matching",
    "compare",
    "save_program",
    "get_program_facts",
    "get_admission_route",
    "get_exam_format",
    "query_dataset",
}


def test_selection_tools_has_eight_named_tools_with_descriptions():
    assert set(SELECTION_TOOLS.names()) == _SELECTION_TOOL_NAMES
    assert len(SELECTION_TOOLS.names()) == 8

    schemas = SELECTION_TOOLS.schemas()

    assert len(schemas) == 8
    for schema in schemas:
        assert schema["function"]["description"]


def test_tutor_tools_has_three_names_and_rejects_save_program():
    assert set(TUTOR_TOOLS.names()) == {"explain_belief", "get_task", "get_exam_format"}

    with pytest.raises(ValueError):
        TUTOR_TOOLS.register(save_program)


async def test_calling_a_stub_tool_raises_not_implemented_error():
    ctx = ToolCtx(student_id="s1", deps=None, request_id="r1")
    args = UpdateProfileArgs(path="traits.summary", value="x").model_dump()

    with pytest.raises(NotImplementedError):
        await SELECTION_TOOLS.call("update_profile", args, ctx)
