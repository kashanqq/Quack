"""PostgreSQL Phase 1 persistence schema."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_student_occurred", "student_id", "occurred_at"),
        Index(
            "ix_events_chat_unprocessed",
            "chat_id",
            "processed_at",
            postgresql_where=text("processed_at IS NULL"),
        ),
        Index("ix_events_type", "type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    session_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    exam_id: Mapped[str | None] = mapped_column(Text)
    set_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    topic_skill_id: Mapped[str | None] = mapped_column(Text)
    chat_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    type: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extractor_version: Mapped[str | None] = mapped_column(Text)
    source_event_ids: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger))


class Profile(Base):
    __tablename__ = "profiles"

    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    questionnaire: Mapped[dict[str, Any]] = mapped_column(JSONB)
    traits: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SavedProgram(Base):
    __tablename__ = "saved_programs"

    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    program_id: Mapped[str] = mapped_column(Text, primary_key=True)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProgramCache(Base):
    __tablename__ = "programs_cache"
    __table_args__ = (
        Index("ix_programs_cache_country", "country"),
        Index("ix_programs_cache_direction", "direction"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    university: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text)
    duration_months: Mapped[int | None] = mapped_column(Integer)
    tuition_per_year: Mapped[int | None] = mapped_column(Integer)
    living_per_year: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(Text)
    scholarships_note: Mapped[str | None] = mapped_column(Text)
    environment_text: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    checked_at: Mapped[date] = mapped_column(Date)
    is_demo: Mapped[bool]
    extracted_auto: Mapped[bool]
    flagged: Mapped[bool]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


class TaskTemplate(Base):
    __tablename__ = "task_templates"
    __table_args__ = (Index("ix_task_templates_skill_exam", "skill_id", "exam_id"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    exam_id: Mapped[str] = mapped_column(Text)
    skill_id: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(Text)
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB)


class TaskInstance(Base):
    __tablename__ = "task_instances"
    __table_args__ = (UniqueConstraint("template_id", "seed", "student_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    template_id: Mapped[str] = mapped_column(Text)
    seed: Mapped[int] = mapped_column(BigInteger)
    exam_id: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    stem_rendered: Mapped[str] = mapped_column(Text)
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    answer: Mapped[Any] = mapped_column(JSONB)
    trap_answers: Mapped[Any | None] = mapped_column(JSONB)
    solution_rendered: Mapped[Any] = mapped_column(JSONB)
    figure_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    skill_id: Mapped[str] = mapped_column(Text)
    time_reference_sec: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text))
    mode: Mapped[str | None] = mapped_column(Text)
    issued_event_id: Mapped[int | None] = mapped_column(BigInteger)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correct: Mapped[bool | None] = mapped_column(Boolean)


class Set(Base):
    __tablename__ = "sets"
    __table_args__ = (
        Index("ix_sets_student_exam_status", "student_id", "exam_id", "status"),
        CheckConstraint(
            "status IN ('upcoming', 'current', 'done')", name="ck_sets_status"
        ),
        CheckConstraint(
            "kind IN ('regular', 'review', 'consolidation')", name="ck_sets_kind"
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    exam_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    deadline: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    rebuilt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SetTopic(Base):
    __tablename__ = "set_topics"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('topic', 'check', 'review')", name="ck_set_topics_kind"
        ),
        CheckConstraint("status IN ('open', 'closed')", name="ck_set_topics_status"),
    )

    set_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sets.id"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(Text, primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)


class DiagnosticRun(Base):
    __tablename__ = "diagnostic_runs"
    __table_args__ = (
        Index(
            "uq_diagnostic_runs_active_student_exam",
            "student_id",
            "exam_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')",
            name="ck_diagnostic_runs_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    exam_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MockRun(Base):
    __tablename__ = "mock_runs"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('mock_set', 'mock_topic', 'mock_misconception')",
            name="ck_mock_runs_kind",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')",
            name="ck_mock_runs_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    exam_id: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    set_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    skill_id: Mapped[str | None] = mapped_column(Text)
    misconception_id: Mapped[str | None] = mapped_column(Text)
    section_name: Mapped[str] = mapped_column(Text)
    instance_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    predicted_before: Mapped[float | None] = mapped_column(Float)
    raw_score: Mapped[float | None] = mapped_column(Float)
    scaled_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MilestoneMark(Base):
    __tablename__ = "milestone_marks"

    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    milestone_key: Mapped[str] = mapped_column(Text, primary_key=True)
    done_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ForecastCache(Base):
    __tablename__ = "forecast_cache"

    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    exam_id: Mapped[str] = mapped_column(Text, primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    as_of_event_id: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SeenTemplate(Base):
    __tablename__ = "seen_templates"

    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    template_id: Mapped[str] = mapped_column(Text, primary_key=True)
    n_seen: Mapped[int] = mapped_column(Integer)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GeneratedText(Base):
    __tablename__ = "generated_texts"
    __table_args__ = (UniqueConstraint("kind", "input_hash"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    input_hash: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SetSummary(Base):
    __tablename__ = "set_summaries"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    set_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    text: Mapped[str] = mapped_column(Text)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_chat_created", "chat_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    chat_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    role: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    markup: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    event_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    kind: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DailyAggregate(Base):
    __tablename__ = "daily_aggregates"

    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    active_minutes: Mapped[int] = mapped_column(Integer)
    tasks_answered: Mapped[int] = mapped_column(Integer)
    messages: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


class StudentState(Base):
    """Client-kept per-student key/value state (frontend `store.ts` bridge)."""

    __tablename__ = "student_state"

    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
