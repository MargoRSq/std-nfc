"""Категории можно скрывать из фильтра

Revision ID: 0027_categories_hidden
Revises: 0026_region_contacts
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0027_categories_hidden"
down_revision = "0026_region_contacts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("categories", "is_hidden")
