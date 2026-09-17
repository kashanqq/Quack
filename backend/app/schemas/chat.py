"""Message persistence contracts from the shared Phase 1 specification."""

from datetime import datetime
from typing import Literal
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
