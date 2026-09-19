"""Program contracts shared by repository consumers."""

from __future__ import annotations

from datetime import date, datetime
from datetime import date as _date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ExamId


class Requirement(BaseModel):
    type: Literal["exam_score", "language", "gpa", "document", "other"]
    exam_id: ExamId | None = None
    threshold: float | None = None
    comparator: Literal[">=", "<=", "range", "present"]
    description: str
    source: str | None = None


class Deadline(BaseModel):
    kind: Literal["application", "scholarship", "exam_registration", "other"]
    date: date
    round: str | None = None
    source: str
    checked_at: date
    is_demo: bool


class Program(BaseModel):
    id: str
    university: str
    country: str
    city: str
    direction: str
    language: str
    duration_months: int | None = None
    tuition_per_year: int | None = None
    living_per_year: int | None = None
    currency: str
    requirements: list[Requirement]
    deadlines: list[Deadline]
    scholarships_note: str | None = None
    environment_text: str | None = None
    source_url: str
    checked_at: date
    is_demo: bool
    extracted_auto: bool
    flagged: bool
    extraction: ExtractionMeta | None = None


class SavedProgram(BaseModel):
    program_id: str
    saved_at: datetime


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str


# --- phase 4: automatic extraction (§6, §14.6) ---


class ExtractionMeta(BaseModel):
    """What the extraction knew about itself — shown next to every number."""

    prompt_version: str
    model: str
    page_chars: int
    dropped_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    search_query: str | None = None
    requested_by: UUID | None = None
    extracted_at: datetime


class ExtractedRequirement(BaseModel):
    type: Literal["exam_score", "language", "gpa", "document", "other"]
    exam_name: str | None = None
    threshold: float | None = None
    comparator: Literal[">=", "<=", "range", "present"] | None = None
    description: str


class ExtractedDeadline(BaseModel):
    kind: Literal["application", "scholarship", "exam_registration", "other"]
    date: _date | None = None
    round: str | None = None
    raw: str


class ExtractedProgram(BaseModel):
    """Structured output of `extract_program_v1`. «Неизвестно» is `None`."""

    university: str | None = None
    country: str | None = None
    city: str | None = None
    direction: str | None = None
    language: str | None = None
    duration_months: int | None = None
    tuition_per_year: int | None = None
    living_per_year: int | None = None
    currency: str | None = None
    requirements: list[ExtractedRequirement] = Field(default_factory=list)
    deadlines: list[ExtractedDeadline] = Field(default_factory=list)
    scholarships_note: str | None = None
    environment_text: str | None = None
    # Поле → короткая цитата из страницы, на которой основано значение.
    evidence: dict[str, str] = Field(default_factory=dict)


class SearchIn(BaseModel):
    query: str = Field(min_length=3, max_length=200)


class SearchStartedOut(BaseModel):
    search_id: str
    status: Literal["queued"] = "queued"


class SearchStatusOut(BaseModel):
    search_id: str
    status: Literal["queued", "running", "done", "unavailable"]
    found: list[str] = Field(default_factory=list)
    rejected: int = 0
    error: str | None = None


class ProgramFlagIn(BaseModel):
    reason: str = Field(max_length=300)


Program.model_rebuild()
