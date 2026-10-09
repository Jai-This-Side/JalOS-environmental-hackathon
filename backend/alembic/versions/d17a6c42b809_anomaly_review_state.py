"""Persist admin review state for household usage anomalies."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d17a6c42b809"
down_revision: Union[str, Sequence[str], None] = "b84e2d7fa901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anomaly_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("flat_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["flat_id"], ["flats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomaly_reviews_flat_id", "anomaly_reviews", ["flat_id"], unique=True)
    op.create_index("ix_anomaly_reviews_updated_at", "anomaly_reviews", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_anomaly_reviews_updated_at", table_name="anomaly_reviews")
    op.drop_index("ix_anomaly_reviews_flat_id", table_name="anomaly_reviews")
    op.drop_table("anomaly_reviews")
