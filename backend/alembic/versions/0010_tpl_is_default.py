"""add is_default flag to templates

Revision ID: 0010_tpl_is_default
Revises: 0009_tpl_default
Create Date: 2026-05-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_tpl_is_default"
down_revision: str | None = "0009_tpl_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "templates",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        "UPDATE templates SET is_default = true WHERE name = 'По умолчанию'"
    )
    op.execute(
        "INSERT INTO templates (name, category_id, default_fields, default_styles, "
        "custom_field_schema, created_by, is_default) "
        "SELECT 'По умолчанию', c.id, '{}'::jsonb, "
        "jsonb_build_object("
        "'bg_kind', 'gradient', "
        "'bg_gradient', jsonb_build_object('start', '#1F1E5E', 'end', '#798BFF', 'angle', 180), "
        "'photo_shape', 'square'), "
        "'[]'::jsonb, NULL, true "
        "FROM categories c WHERE c.code = 'bronze' "
        "AND NOT EXISTS (SELECT 1 FROM templates WHERE is_default = true) "
        "ON CONFLICT (name, category_id) DO NOTHING"
    )
    op.create_index(
        "uq_templates_one_default",
        "templates",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_templates_one_default", table_name="templates")
    op.drop_column("templates", "is_default")
