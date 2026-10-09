"""Track resident and admin alert reads independently."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "65f8c49d2b31"
down_revision: Union[str, Sequence[str], None] = "d17a6c42b809"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "alert_id", name="uq_alert_reads_user_alert"),
    )
    op.create_index("ix_alert_reads_alert_id", "alert_reads", ["alert_id"], unique=False)
    op.create_index("ix_alert_reads_user_id", "alert_reads", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alert_reads_user_id", table_name="alert_reads")
    op.drop_index("ix_alert_reads_alert_id", table_name="alert_reads")
    op.drop_table("alert_reads")
