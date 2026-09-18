"""Message persistence contracts from the shared Phase 1 specification."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AssistantMarkup(BaseModel):
    mode: str | None = None
    gave_task_instance_id: UUID | None = None
    hint_level: int | None = None
    referenced_skill_ids: list[str] = Field(default_factory=list)


class MessageOut(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    text: str
    markup: AssistantMarkup | None = None
    event_id: int
    created_at: datetime


ChatKind = Literal["selection", "prep"]


class ChatMessageIn(BaseModel):
    text: str = Field(max_length=4000)
    topic_skill_id: str | None = None
    set_id: UUID | None = None


class TextDelta(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    text: str


class ToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool: str
    args: dict[str, Any]
    call_id: str


class ToolResult(BaseModel):
    """Результат инструмента: `data` уходит на фронт, `model_data` — модели.

    Карточки подбора рендерит фронт, поэтому `data` — полный ответ
    инструмента. Модели тот же объём не нужен (`run_matching` с limit=10 —
    это 3–4 КБ JSON в контексте на каждый ход), поэтому инструмент может
    отдать отдельную сжатую проекцию; `model_data is None` означает «модели
    показываем то же, что и фронту». В поток SSE поле не сериализуется.
    """

    type: Literal["tool_result"] = "tool_result"
    tool: str
    call_id: str
    data: Any
    model_data: Any | None = Field(default=None, exclude=True)
    error: str | None = None


class Done(BaseModel):
    type: Literal["done"] = "done"
    event_id: int
    mode: str | None = None
    gave_task_instance_id: UUID | None = None
    hint_level: int | None = None
    referenced_skill_ids: list[str] = Field(default_factory=list)


class StreamError(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


StreamEvent = Annotated[
    TextDelta | ToolCall | ToolResult | Done | StreamError,
    Field(discriminator="type"),
]


class ChatCtx(BaseModel):
    student_id: UUID
    kind: ChatKind
    chat_id: UUID
    session_id: UUID
    request_id: str
    topic_skill_id: str | None = None
    set_id: UUID | None = None
