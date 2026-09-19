"""SELECTION_TOOLS / TUTOR_TOOLS registries (docs/tz/30-B2.md §5.2-§5.3, §6,
tests/agents/test_registries.py)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agents.selection import SELECTION_TOOLS, UpdateProfileArgs, save_program
from app.agents.tutor import TUTOR_TOOLS
from app.errors import ValidationFailed
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


async def test_unknown_profile_path_is_rejected_before_any_io():
    """Phase 3: the body is real; a path outside the questionnaire fails
    validation before the tool touches a database."""
    ctx = ToolCtx(student_id=str(uuid4()), deps=None, request_id="r1")
    args = UpdateProfileArgs(path="secret.field", value="x").model_dump()

    with pytest.raises(ValidationFailed, match="unknown profile path"):
        await SELECTION_TOOLS.call("update_profile", args, ctx)


def test_subset_keeps_specs_and_read_only_flag():
    subset = SELECTION_TOOLS.subset(["update_profile", "query_dataset", "nope"])
    assert subset.names() == ["update_profile", "query_dataset"]

    tutor_subset = TUTOR_TOOLS.subset(["get_task"])
    with pytest.raises(ValueError):
        tutor_subset.register(save_program)
