"""Internal read model for cached generated text."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GeneratedText(BaseModel):
    id: UUID
    kind: str
    input_hash: str
    text: str
    model: str
    prompt_version: str
    created_at: datetime
