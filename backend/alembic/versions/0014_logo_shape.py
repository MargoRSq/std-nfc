"""add logo_shape to cards

Revision ID: 0014_logo_shape
Revises: 0013_avatar_color
Create Date: 2026-05-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_logo_shape"
down_revision: str | None = "0013_avatar_color"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column("logo_shape", sa.Text(), nullable=False, server_default=sa.text("'square'")),
    )
    op.create_check_constraint(
        "ck_cards_logo_shape",
        "cards",
        "logo_shape IN ('square', 'circle', 'rectangle')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cards_logo_shape", "cards", type_="check")
    op.drop_column("cards", "logo_shape")
