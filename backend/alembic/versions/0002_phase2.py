"""Add the Phase 2 PostgreSQL persistence schema."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_phase2"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("task_instances", sa.Column("mode", sa.Text(), nullable=True))
    op.add_column(
        "task_instances", sa.Column("issued_event_id", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "task_instances",
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("task_instances", sa.Column("correct", sa.Boolean(), nullable=True))

    op.create_table(
        "sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exam_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "rebuilt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('upcoming', 'current', 'done')", name="ck_sets_status"
        ),
        sa.CheckConstraint(
            "kind IN ('regular', 'review', 'consolidation')", name="ck_sets_kind"
        ),
    )
    op.create_index(
        "ix_sets_student_exam_status", "sets", ["student_id", "exam_id", "status"]
    )

    op.create_table(
        "set_topics",
        sa.Column(
            "set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sets.id"),
            primary_key=True,
        ),
        sa.Column("skill_id", sa.Text(), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('topic', 'check', 'review')", name="ck_set_topics_kind"
        ),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_set_topics_status"),
    )

    op.create_table(
        "diagnostic_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exam_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')",
            name="ck_diagnostic_runs_status",
        ),
    )
    op.create_index(
        "uq_diagnostic_runs_active_student_exam",
        "diagnostic_runs",
        ["student_id", "exam_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "mock_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exam_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skill_id", sa.Text(), nullable=True),
        sa.Column("misconception_id", sa.Text(), nullable=True),
        sa.Column("section_name", sa.Text(), nullable=False),
        sa.Column(
            "instance_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
        ),
        sa.Column("predicted_before", sa.Float(), nullable=True),
        sa.Column("raw_score", sa.Float(), nullable=True),
        sa.Column("scaled_score", sa.Float(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('mock_set', 'mock_topic', 'mock_misconception')",
            name="ck_mock_runs_kind",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')", name="ck_mock_runs_status"
        ),
    )

    op.create_table(
        "milestone_marks",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("milestone_key", sa.Text(), primary_key=True),
        sa.Column(
            "done_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "forecast_cache",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("exam_id", sa.Text(), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("as_of_event_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("forecast_cache")
    op.drop_table("milestone_marks")
    op.drop_table("mock_runs")
    op.drop_index(
        "uq_diagnostic_runs_active_student_exam", table_name="diagnostic_runs"
    )
    op.drop_table("diagnostic_runs")
    op.drop_table("set_topics")
    op.drop_index("ix_sets_student_exam_status", table_name="sets")
    op.drop_table("sets")

    op.drop_column("task_instances", "correct")
    op.drop_column("task_instances", "answered_at")
    op.drop_column("task_instances", "issued_event_id")
    op.drop_column("task_instances", "mode")
