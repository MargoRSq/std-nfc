"""avatar_color + avatar_gradient on cards

Revision ID: 0013_avatar_color
Revises: 0012_internal_blocks
Create Date: 2026-05-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0013_avatar_color"
down_revision: str | None = "0012_internal_blocks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("avatar_color", sa.Text(), nullable=True))
    op.add_column("cards", sa.Column("avatar_gradient", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("cards", "avatar_gradient")
    op.drop_column("cards", "avatar_color")
