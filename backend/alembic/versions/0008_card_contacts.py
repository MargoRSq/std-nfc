"""add contacts JSONB column to cards

Revision ID: 0008_card_contacts
Revises: 0007_seed_default_templates
Create Date: 2026-05-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0008_card_contacts"
down_revision: str | None = "0007_seed_default_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column(
            "contacts",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("cards", "contacts")
