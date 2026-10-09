"""Add private optional photo attachments to complaints."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b84e2d7fa901"
down_revision: Union[str, Sequence[str], None] = "42d59c43c1dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("complaints", sa.Column("photo_path", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("complaints", "photo_path")
