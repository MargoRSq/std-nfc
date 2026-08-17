"""Дата исключения из СТД

Revision ID: 0030_exclusion_date
Revises: 0029_normalize_gradients
Create Date: 2026-08-17

По ТЗ на билете нужна дата исключения, а хранился только год. Год оставляем
как есть — он заполнен у части карточек и уезжает в выгрузку; новое поле
заполняется отдельно, на карточке дата имеет приоритет над годом.
"""

import sqlalchemy as sa
from alembic import op

revision = "0030_exclusion_date"
down_revision = "0029_normalize_gradients"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("exclusion_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("cards", "exclusion_date")
