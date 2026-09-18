"""Tool registry: schema generation, dispatch, and the read-only rule
(docs/tz/30-B2.md §4.1, §6, tests/llm/test_tools.py)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from app.errors import ValidationFailed
from app.llm.tools import ToolCtx, ToolRegistry, tool

pytestmark = pytest.mark.phase1


class _EchoArgs(BaseModel):
    x: int = Field(description="the integer to echo back")


@tool(name="echo_tool", description="echoes x back")
async def _echo(args: _EchoArgs, ctx: ToolCtx) -> dict:
    return {"x": args.x}


def _ctx() -> ToolCtx:
    return ToolCtx(student_id="s1", deps=None, request_id="r1")


def test_tool_decorator_produces_schema_with_field_descriptions():
    registry = ToolRegistry()
    registry.register(_echo)

    schemas = registry.schemas()

    assert schemas[0]["function"]["name"] == "echo_tool"
    parameters = schemas[0]["function"]["parameters"]
    assert parameters["properties"]["x"]["description"] == "the integer to echo back"


async def test_call_dispatches_validates_and_raises_for_unknown_name():
    registry = ToolRegistry()
    registry.register(_echo)
    ctx = _ctx()

    assert await registry.call("echo_tool", {"x": 1}, ctx) == {"x": 1}

    with pytest.raises(ValidationFailed):
        await registry.call("echo_tool", {"x": "bad"}, ctx)

    with pytest.raises(KeyError):
        await registry.call("nope", {}, ctx)


def test_register_duplicate_name_raises_value_error():
    registry = ToolRegistry()
    registry.register(_echo)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_echo)


def test_read_only_registry_rejects_non_read_only_spec():
    @tool(name="writes_stuff", description="mutates something", read_only=False)
    async def _writer(args: _EchoArgs, ctx: ToolCtx) -> dict:
        return {}

    registry = ToolRegistry(read_only=True)

    with pytest.raises(ValueError, match="read-only"):
        registry.register(_writer)


def test_tool_decorator_rejects_bad_signatures_at_import_time():
    with pytest.raises(TypeError):

        @tool(name="one_param", description="d")
        async def _one_param(args: _EchoArgs) -> dict:
            return {}

    with pytest.raises(TypeError):

        @tool(name="no_annotation", description="d")
        async def _no_annotation(args, ctx) -> dict:
            return {}


class _Result(BaseModel):
    y: int


@tool(name="returns_model", description="returns a pydantic result")
async def _returns_model(args: _EchoArgs, ctx: ToolCtx) -> _Result:
    return _Result(y=args.x)


async def test_pydantic_result_is_serialized_to_dict():
    registry = ToolRegistry()
    registry.register(_returns_model)

    result = await registry.call("returns_model", {"x": 5}, _ctx())

    assert result == {"y": 5}
