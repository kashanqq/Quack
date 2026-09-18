"""LLM client contracts from the shared Phase 1 specification (00-contracts.md §6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ModelSlot = Literal["chat", "bulk"]


class ToolCallOut(BaseModel):
    call_id: str
    name: str
    args: dict


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCallOut] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class LLMUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int


class LLMResult(BaseModel):
    text: str
    tool_calls: list[ToolCallOut] = Field(default_factory=list)
    usage: LLMUsage | None
    finish_reason: str


LLMStatus = Literal["ok", "degraded", "down"]
