"""Phase 5 — durable job intents and the recovery backlog index.

Expand-only (§9.4): every new `job_outbox` column is added with a server
default so rows written by the phase-4 code keep working, and the backfill
only looks at what the old protocol could actually say. `enqueued_at IS NOT
NULL` means "ARQ accepted the delivery", which is not proof the job ran — the
row becomes `enqueued`, not `succeeded`, and the replay re-checks it. A row
that was still waiting becomes `pending`.

No existing column is dropped or retyped, so the previous application version
keeps running against this schema while the rollout finishes.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004_phase5"
down_revision = "0003_phase4"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("status", sa.Text(), "'pending'", False),
    ("dependency", sa.Text(), None, True),
    ("attempts", sa.Integer(), "0", False),
    ("not_before", sa.DateTime(timezone=True), "now()", False),
    ("lease_until", sa.DateTime(timezone=True), None, True),
    ("lease_token", postgresql.UUID(as_uuid=True), None, True),
    ("updated_at", sa.DateTime(timezone=True), "now()", False),
    ("last_error_code", sa.Text(), None, True),
)


def upgrade() -> None:
    for name, type_, default, nullable in _COLUMNS:
        op.add_column(
            "job_outbox",
            sa.Column(
                name,
                type_,
                nullable=nullable,
                server_default=sa.text(default) if default else None,
            ),
        )

    # Backfill: the only durable signal the old rows carry is `enqueued_at`.
    op.execute(
        "UPDATE job_outbox SET status = 'enqueued', not_before = created_at, "
        "updated_at = coalesce(enqueued_at, created_at) "
        "WHERE enqueued_at IS NOT NULL"
    )
    op.execute(
        "UPDATE job_outbox SET status = 'pending', not_before = created_at, "
        "updated_at = created_at WHERE enqueued_at IS NULL"
    )

    op.create_check_constraint(
        "ck_job_outbox_status",
        "job_outbox",
        "status IN ('pending','enqueued','running','waiting_dependency',"
        "'succeeded','failed','cancelled')",
    )
    op.create_check_constraint(
        "ck_job_outbox_dependency",
        "job_outbox",
        "dependency IS NULL OR dependency IN ('llm','graph','search','redis')",
    )
    op.create_check_constraint("ck_job_outbox_attempts", "job_outbox", "attempts >= 0")

    op.create_index("ix_job_outbox_due", "job_outbox", ["status", "not_before", "id"])
    op.create_index(
        "ix_job_outbox_lease",
        "job_outbox",
        ["lease_until", "id"],
        postgresql_where=sa.text("status IN ('enqueued','running')"),
    )
    # One live intent per logical job; a finished row does not block the next
    # batch of the same recommendation a day later (§9.2).
    op.create_index(
        "uq_job_outbox_active",
        "job_outbox",
        ["queue", "job_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('pending','enqueued','running','waiting_dependency')"
        ),
    )

    op.create_index(
        "ix_events_unprocessed",
        "events",
        ["student_id", "id"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_events_unprocessed", table_name="events")
    op.drop_index("uq_job_outbox_active", table_name="job_outbox")
    op.drop_index("ix_job_outbox_lease", table_name="job_outbox")
    op.drop_index("ix_job_outbox_due", table_name="job_outbox")
    op.drop_constraint("ck_job_outbox_attempts", "job_outbox", type_="check")
    op.drop_constraint("ck_job_outbox_dependency", "job_outbox", type_="check")
    op.drop_constraint("ck_job_outbox_status", "job_outbox", type_="check")
    for name, *_ in reversed(_COLUMNS):
        op.drop_column("job_outbox", name)
