"""add field_order to cards

Revision ID: 0015_field_order
Revises: 0014_logo_shape
Create Date: 2026-05-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0015_field_order"
down_revision: str | None = "0014_logo_shape"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column(
            "field_order",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("cards", "field_order")
