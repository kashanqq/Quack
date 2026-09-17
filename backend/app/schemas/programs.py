"""Program contracts shared by repository consumers."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

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


class SavedProgram(BaseModel):
    program_id: str
    saved_at: datetime
