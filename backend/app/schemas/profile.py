"""Profile contracts shared by repository consumers."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ProfileFieldMark = Literal["stated", "assumed", "default"]


class ProfileField[T](BaseModel):
    value: T | None = None
    mark: ProfileFieldMark = "default"
    updated_at: datetime | None = None


class Level(BaseModel):
    grade: ProfileField[int] = Field(default_factory=ProfileField[int])
    admission_year: ProfileField[int] = Field(default_factory=ProfileField[int])


class Direction(BaseModel):
    field: ProfileField[str] = Field(default_factory=ProfileField[str])
    alternatives: ProfileField[list[str]] = Field(
        default_factory=ProfileField[list[str]]
    )


class Academics(BaseModel):
    self_assessment: ProfileField[dict[str, int]] = Field(
        default_factory=ProfileField[dict[str, int]]
    )
    ent_trial_score: ProfileField[int] = Field(default_factory=ProfileField[int])
    ent_profile_pair: ProfileField[list[str]] = Field(
        default_factory=ProfileField[list[str]]
    )
    sat_score: ProfileField[int] = Field(default_factory=ProfileField[int])
    sat_target: ProfileField[int] = Field(default_factory=ProfileField[int])
    sat_date: ProfileField[date] = Field(default_factory=ProfileField[date])
    ielts_score: ProfileField[float] = Field(default_factory=ProfileField[float])
    ielts_target: ProfileField[float] = Field(default_factory=ProfileField[float])


class Preferences(BaseModel):
    countries: ProfileField[list[str]] = Field(default_factory=ProfileField[list[str]])
    cities: ProfileField[list[str]] = Field(default_factory=ProfileField[list[str]])
    language: ProfileField[str] = Field(default_factory=ProfileField[str])
    budget_per_year: ProfileField[int] = Field(default_factory=ProfileField[int])
    currency: ProfileField[str] = Field(default_factory=ProfileField[str])
    grant_need: ProfileField[Literal["only_grant", "preferred", "not_needed"]] = Field(
        default_factory=ProfileField[Literal["only_grant", "preferred", "not_needed"]]
    )


class Constraints(BaseModel):
    required: ProfileField[list[str]] = Field(default_factory=ProfileField[list[str]])
    excluded: ProfileField[list[str]] = Field(default_factory=ProfileField[list[str]])


class Priorities(BaseModel):
    ranking: ProfileField[
        list[
            Literal[
                "realism",
                "cost",
                "ranking",
                "location",
                "program",
                "research",
                "mobility",
            ]
        ]
    ] = Field(
        default_factory=ProfileField[
            list[
                Literal[
                    "realism",
                    "cost",
                    "ranking",
                    "location",
                    "program",
                    "research",
                    "mobility",
                ]
            ]
        ]
    )


class Pace(BaseModel):
    hours_per_week: ProfileField[int] = Field(default_factory=ProfileField[int])
    explanation_depth: ProfileField[Literal["short", "normal", "deep"]] = Field(
        default_factory=ProfileField[Literal["short", "normal", "deep"]]
    )
    hint_level: ProfileField[Literal["minimal", "normal", "generous"]] = Field(
        default_factory=ProfileField[Literal["minimal", "normal", "generous"]]
    )


class Questionnaire(BaseModel):
    level: Level = Field(default_factory=Level)
    direction: Direction = Field(default_factory=Direction)
    academics: Academics = Field(default_factory=Academics)
    preferences: Preferences = Field(default_factory=Preferences)
    constraints: Constraints = Field(default_factory=Constraints)
    priorities: Priorities = Field(default_factory=Priorities)
    pace: Pace = Field(default_factory=Pace)


class Traits(BaseModel):
    verbatim: list[str] = Field(default_factory=list)
    summary: str = ""


class Profile(BaseModel):
    student_id: UUID
    questionnaire: Questionnaire = Field(default_factory=Questionnaire)
    traits: Traits = Field(default_factory=Traits)
    readiness: float = Field(default=0.0, ge=0, le=1)


class ProfileUpdateIn(BaseModel):
    path: str
    value: Any
    by: Literal["assistant", "user"]
