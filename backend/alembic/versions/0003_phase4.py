"""Phase 4 — background generation, soft match, Quack and extraction.

One migration per phase (docs/tz/40-phase4-background-quack.md §1.7).
`recommendations` is empty before this phase, so `reason_hash` is not
backfilled: the column is added with an empty default and the partial
unique index only constrains rows the phase-4 batch writes.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_phase4"
down_revision = "0002_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- generated_texts: status, subject and the per-student lookup ---
    op.alter_column("generated_texts", "text", nullable=True)
    op.add_column(
        "generated_texts",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "generated_texts",
        sa.Column("subject", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "generated_texts",
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "generated_texts",
        sa.Column("status", sa.Text(), nullable=False, server_default="ready"),
    )
    op.add_column(
        "generated_texts",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("generated_texts", sa.Column("error", sa.Text(), nullable=True))
    op.add_column(
        "generated_texts",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_generated_texts_subject",
        "generated_texts",
        ["student_id", "kind", "subject", sa.text("created_at DESC")],
    )

    # --- set_summaries: one row per set, generating until the text lands ---
    op.alter_column("set_summaries", "text", nullable=True)
    op.add_column("set_summaries", sa.Column("exam_id", sa.Text(), nullable=True))
    op.add_column(
        "set_summaries",
        sa.Column("status", sa.Text(), nullable=False, server_default="ready"),
    )
    op.add_column(
        "set_summaries", sa.Column("prompt_version", sa.Text(), nullable=True)
    )
    op.add_column("set_summaries", sa.Column("input_hash", sa.Text(), nullable=True))
    op.add_column(
        "set_summaries",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint("uq_set_summaries_set_id", "set_summaries", ["set_id"])

    # --- recommendations: the Quack feed ---
    op.add_column(
        "recommendations",
        sa.Column("reason_hash", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "recommendations",
        sa.Column("urgency", sa.Text(), nullable=False, server_default="normal"),
    )
    op.add_column(
        "recommendations",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("recommendations", sa.Column("exam_id", sa.Text(), nullable=True))
    op.add_column(
        "recommendations",
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column("decision_event_id", sa.BigInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_recommendations_status",
        "recommendations",
        "status IN ('pending', 'shown', 'accepted', 'declined', 'expired')",
    )
    op.create_index(
        "uq_recommendations_open_reason",
        "recommendations",
        ["student_id", "reason_hash"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'shown')"),
    )
    op.create_index(
        "ix_recommendations_student_status",
        "recommendations",
        ["student_id", "status"],
    )

    # --- student_aggregates ---
    op.create_table(
        "student_aggregates",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("as_of_event_id", sa.BigInteger(), nullable=False),
    )

    # --- soft_matches ---
    op.create_table(
        "soft_matches",
        sa.Column("summary_hash", sa.Text(), primary_key=True),
        sa.Column("program_id", sa.Text(), primary_key=True),
        sa.Column("prompt_version", sa.Text(), primary_key=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("caveat", sa.Text(), nullable=True),
        sa.Column("matched_traits", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("confidence", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_soft_matches_program", "soft_matches", ["program_id"])

    # --- programs_cache: extraction metadata and de-duplication keys ---
    op.add_column(
        "programs_cache", sa.Column("extraction", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "programs_cache", sa.Column("normalized_url", sa.Text(), nullable=True)
    )
    op.add_column(
        "programs_cache", sa.Column("university_slug", sa.Text(), nullable=True)
    )
    op.add_column(
        "programs_cache", sa.Column("direction_slug", sa.Text(), nullable=True)
    )
    op.create_index(
        "uq_programs_cache_normalized_url",
        "programs_cache",
        ["normalized_url"],
        unique=True,
    )
    op.create_index(
        "ix_programs_cache_slugs",
        "programs_cache",
        ["university_slug", "direction_slug"],
    )

    # --- job_outbox: only for enqueues Redis refused ---
    op.create_table(
        "job_outbox",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("queue", sa.Text(), nullable=False),
        sa.Column("fn_name", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("kwargs", postgresql.JSONB(), nullable=False),
        sa.Column("defer_by", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_job_outbox_pending",
        "job_outbox",
        ["created_at"],
        postgresql_where=sa.text("enqueued_at IS NULL"),
    )

    # --- sets: forecast snapshot taken when the set is opened ---
    op.add_column(
        "sets", sa.Column("opened_forecast", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("sets", "opened_forecast")

    op.drop_index("ix_job_outbox_pending", table_name="job_outbox")
    op.drop_table("job_outbox")

    op.drop_index("ix_programs_cache_slugs", table_name="programs_cache")
    op.drop_index("uq_programs_cache_normalized_url", table_name="programs_cache")
    op.drop_column("programs_cache", "direction_slug")
    op.drop_column("programs_cache", "university_slug")
    op.drop_column("programs_cache", "normalized_url")
    op.drop_column("programs_cache", "extraction")

    op.drop_index("ix_soft_matches_program", table_name="soft_matches")
    op.drop_table("soft_matches")
    op.drop_table("student_aggregates")

    op.drop_index("ix_recommendations_student_status", table_name="recommendations")
    op.drop_index("uq_recommendations_open_reason", table_name="recommendations")
    op.drop_constraint("ck_recommendations_status", "recommendations", type_="check")
    for column in (
        "decision_event_id",
        "batch_id",
        "expires_at",
        "shown_at",
        "exam_id",
        "position",
        "urgency",
        "reason_hash",
    ):
        op.drop_column("recommendations", column)

    op.drop_constraint("uq_set_summaries_set_id", "set_summaries", type_="unique")
    for column in ("updated_at", "input_hash", "prompt_version", "status", "exam_id"):
        op.drop_column("set_summaries", column)
    op.execute("UPDATE set_summaries SET text = '' WHERE text IS NULL")
    op.alter_column("set_summaries", "text", nullable=False)

    op.drop_index("ix_generated_texts_subject", table_name="generated_texts")
    for column in (
        "updated_at",
        "error",
        "attempts",
        "status",
        "set_id",
        "subject",
        "student_id",
    ):
        op.drop_column("generated_texts", column)
    op.execute("DELETE FROM generated_texts WHERE text IS NULL")
    op.alter_column("generated_texts", "text", nullable=False)
