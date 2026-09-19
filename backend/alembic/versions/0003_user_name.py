"""Add the display name to users."""

import sqlalchemy as sa

from alembic import op

revision = "0003_user_name"
down_revision = "0002_phase2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "name")
