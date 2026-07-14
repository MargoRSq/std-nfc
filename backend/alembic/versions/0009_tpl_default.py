"""rename existing 'Бронзовые' template to 'По умолчанию'

Revision ID: 0009_tpl_default
Revises: 0008_card_contacts
Create Date: 2026-05-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_tpl_default"
down_revision: str | None = "0008_card_contacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        "DELETE FROM templates "
        "WHERE name = 'По умолчанию' "
        "AND category_id IN (SELECT id FROM categories WHERE code = 'bronze') "
        "AND EXISTS (SELECT 1 FROM templates WHERE name = 'Бронзовые')"
    )
    conn.exec_driver_sql(
        "UPDATE templates "
        "SET name = 'По умолчанию', "
        "default_styles = jsonb_build_object("
        "'bg_kind', 'gradient', "
        "'bg_gradient', jsonb_build_object('start', '#1F1E5E', 'end', '#798BFF', 'angle', 180), "
        "'photo_shape', 'circle') "
        "WHERE name = 'Бронзовые'"
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("UPDATE templates SET name = 'Бронзовые' WHERE name = 'По умолчанию'")
