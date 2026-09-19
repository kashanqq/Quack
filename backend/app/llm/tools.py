"""Tool registry — plain Python functions with Pydantic arguments, no I/O.

Generates OpenAI-format ``tools`` JSON Schema and dispatches calls by name.
Bodies are the caller's concern: this module only validates, routes, and
serializes.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from app.errors import ValidationFailed
from app.schemas.agents import TurnState
from app.schemas.chat import ChatCtx

if TYPE_CHECKING:
    from app.agents.router import AgentDeps


class ToolPayload(BaseModel):
    """Two views of one tool result — see `schemas.chat.ToolResult`.

    `data` — то, что рендерит фронт; `model_data` — сжатая проекция для
    контекста модели. Инструмент возвращает `ToolPayload`, только если эти
    два представления действительно разные.
    """

    data: Any = None
    model_data: Any = None


@dataclass
class ToolCtx:
    """What a tool body gets besides its arguments.

    `chat` — the turn's chat (`chat_id`, `set_id`, `topic_skill_id` for
    `get_task`); `turn` — counters shared by every call of one turn (one task
    per turn, matching calls). Both default, so phase-1 call sites still work.
    """

    student_id: str
    deps: AgentDeps
    request_id: str
    chat: ChatCtx | None = None
    turn: TurnState = field(default_factory=TurnState)


@dataclass
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    fn: Callable[[BaseModel, ToolCtx], Awaitable[Any]]
    read_only: bool = True


def tool(
    name: str, description: str, read_only: bool = True
) -> Callable[[Callable], ToolSpec]:
    def decorator(fn: Callable) -> ToolSpec:
        signature = inspect.signature(fn, eval_str=True)
        params = list(signature.parameters.values())
        if len(params) != 2:
            raise TypeError(
                f"tool {fn.__name__!r} must take exactly two parameters "
                f"(args, ctx), got {len(params)}"
            )
        args_model = params[0].annotation
        if not (isinstance(args_model, type) and issubclass(args_model, BaseModel)):
            raise TypeError(
                f"tool {fn.__name__!r} first parameter must be annotated "
                "with a BaseModel subclass"
            )
        return ToolSpec(
            name=name,
            description=description,
            args_model=args_model,
            fn=fn,
            read_only=read_only,
        )

    return decorator


class ToolRegistry:
    def __init__(self, read_only: bool = False) -> None:
        self._read_only = read_only
        self._specs: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"tool {spec.name!r} already registered")
        if self._read_only and not spec.read_only:
            raise ValueError(
                f"tool {spec.name!r} is not read-only, registry is read-only"
            )
        self._specs[spec.name] = spec

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.args_model.model_json_schema(),
                },
            }
            for spec in self._specs.values()
        ]

    async def call(self, name: str, args: dict, ctx: ToolCtx) -> Any:
        spec = self._specs[name]
        try:
            parsed_args = spec.args_model.model_validate(args)
        except ValidationError as exc:
            raise ValidationFailed(str(exc)) from exc
        result = await spec.fn(parsed_args, ctx)
        if isinstance(result, ToolPayload):
            return result
        if isinstance(result, BaseModel):
            return result.model_dump(mode="json")
        return result

    def names(self) -> list[str]:
        return list(self._specs.keys())

    def subset(self, names: list[str]) -> ToolRegistry:
        """A new registry with only these tools (same specs, same read-only
        flag) — the per-turn access policy; unknown names are ignored."""
        registry = ToolRegistry(read_only=self._read_only)
        for name in names:
            spec = self._specs.get(name)
            if spec is not None:
                registry.register(spec)
        return registry
