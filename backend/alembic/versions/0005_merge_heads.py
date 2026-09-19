"""Merge the user-name/state branch with the phase 4-5 branch."""

revision = "0005_merge_heads"
down_revision = ("0004_phase5", "0004_student_state")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
