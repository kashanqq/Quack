"""Generated text contracts — the cache row, the read model and the inputs.

Phase 4 (docs/tz/40-phase4-background-quack.md §3, §14.2). The input models
live here rather than in `app/agents/texts.py` (B2) on purpose: `app/apply`
collects them and must not import the agents layer (`tests/test_layers.py`),
while the hash over them has to be identical on both sides.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import (
    ExamId,
    GeneratedTextStatus,
    SkillLevel,
    TextKind,
    TextMark,
)


class GeneratedText(BaseModel):
    """One row of `generated_texts` as the repository returns it."""

    id: UUID
    kind: str
    input_hash: str
    text: str | None = None
    model: str
    prompt_version: str
    created_at: datetime
    student_id: UUID | None = None
    subject: str = ""
    set_id: UUID | None = None
    status: Literal["generating", "ready", "failed"] = "ready"
    attempts: int = 0
    error: str | None = None
    updated_at: datetime | None = None


class GeneratedTextOut(BaseModel):
    """What `GET /texts/{set_id}/{skill_id}` returns (§14.2)."""

    kind: TextKind
    subject: str
    set_id: UUID | None = None
    status: GeneratedTextStatus
    text: str | None = None
    mark: TextMark | None = None
    prompt_version: str | None = None
    generated_at: datetime | None = None
    input_hash: str
    reason: str | None = None


class TextOpenedIn(BaseModel):
    kind: Literal["guideline", "explanation"]


# --- inputs of the two set texts (§3.2) ---


class SkillBrief(BaseModel):
    id: str
    name: str
    description: str
    exam_id: ExamId
    area_name: str = ""


class PrerequisiteBrief(BaseModel):
    id: str
    name: str
    level: SkillLevel


class MisconceptionBrief(BaseModel):
    id: str
    name: str
    description: str
    trigger_words: str | None = None


class SetBrief(BaseModel):
    deadline: date | None = None
    position_in_set: int = 0
    n_topics: int = 0
    kind: Literal["regular", "review", "consolidation"] = "regular"


class ProfileBrief(BaseModel):
    """Only what actually shapes the wording.

    `hours_per_week` is deliberately absent (§16 item 5, decided): accepting
    a `more_hours` recommendation would otherwise invalidate every guideline
    of the set, and the pace barely changes «что решать».
    """

    explanation_depth: Literal["short", "normal", "deep"] = "normal"
    hint_level: Literal["minimal", "normal", "generous"] = "normal"


class ExamFormatHint(BaseModel):
    task_types: list[str] = Field(default_factory=list)
    calculator: bool = False


class GuidelineInputs(BaseModel):
    skill: SkillBrief
    state_words: SkillLevel
    p_target_words: str
    prerequisites: list[PrerequisiteBrief] = Field(default_factory=list)
    active_misconceptions: list[MisconceptionBrief] = Field(default_factory=list)
    root_of: list[str] = Field(default_factory=list)
    set: SetBrief = Field(default_factory=SetBrief)
    profile: ProfileBrief = Field(default_factory=ProfileBrief)
    exam_format_hint: ExamFormatHint = Field(default_factory=ExamFormatHint)
    template_tags: list[str] = Field(default_factory=list)
    mode: Literal["topic", "review"] = "topic"


class ExplanationInputs(BaseModel):
    skill: SkillBrief
    prerequisites: list[str] = Field(default_factory=list)
    exam_format_hint: ExamFormatHint = Field(default_factory=ExamFormatHint)
    explanation_depth: Literal["short", "normal", "deep"] = "normal"


class ProgramBrief(BaseModel):
    university: str
    country: str
    city: str
    language: str
    direction: str
    environment_text: str | None = None
    scholarships_note: str | None = None


class SoftMatchInputs(BaseModel):
    """§5.3 — nothing the hard filter already decided goes in here."""

    traits_summary: str
    traits_verbatim: list[str] = Field(default_factory=list)
    program: ProgramBrief


# --- structured outputs of the six phase-4 prompts (§3.3, §4.4, §5.4, §7) ---


class GuidelineOut(BaseModel):
    how_to_prepare: str
    must_know: list[str]
    traps: list[str] = Field(default_factory=list)
    what_to_solve: list[str]
    summary: str


class ExplanationOut(BaseModel):
    text: str
    key_points: list[str]


class SetSummaryTextOut(BaseModel):
    text: str
    tone: Literal["encouraging"] = "encouraging"


class RealismTextOut(BaseModel):
    text: str


class CompareTextOut(BaseModel):
    conclusion: str
