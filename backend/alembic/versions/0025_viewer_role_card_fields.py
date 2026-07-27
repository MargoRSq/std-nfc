"""Роль viewer + служебные поля карточки (год исключения, дата смерти)

Revision ID: 0025_viewer_role_card_fields
Revises: 0024_rename_default_template
Create Date: 2026-07-27

Имя check-констрейнта пишем явно (`ck_users_role_value`): naming_convention
добавляет префикс, и короткое имя в drop_constraint не находится.
"""

import sqlalchemy as sa
from alembic import op

revision = "0025_viewer_role_card_fields"
down_revision = "0024_rename_default_template"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role_value")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_role_value "
        "CHECK (role IN ('super_admin', 'admin', 'viewer'))"
    )
    op.add_column("cards", sa.Column("exclusion_year", sa.SmallInteger(), nullable=True))
    op.add_column("cards", sa.Column("death_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("cards", "death_date")
    op.drop_column("cards", "exclusion_year")
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'viewer'")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role_value")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_role_value "
        "CHECK (role IN ('super_admin', 'admin'))"
    )
