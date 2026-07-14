"""label_presets table + cards.field_labels

Revision ID: 0017_label_presets
Revises: 0016_membership_no_unique
Create Date: 2026-05-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0017_label_presets"
down_revision: str | None = "0016_membership_no_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "label_presets",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "admin_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("order_idx", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("admin_id", "name", name="uq_label_presets_admin_name"),
    )
    op.create_index(
        "ix_label_presets_admin_order", "label_presets", ["admin_id", "order_idx"]
    )
    op.create_index("label_presets_created_at_idx", "label_presets", ["created_at"])
    op.create_index("label_presets_updated_at_idx", "label_presets", ["updated_at"])

    op.add_column(
        "cards",
        sa.Column(
            "field_labels",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("cards", "field_labels")
    op.drop_index("label_presets_updated_at_idx", table_name="label_presets")
    op.drop_index("label_presets_created_at_idx", table_name="label_presets")
    op.drop_index("ix_label_presets_admin_order", table_name="label_presets")
    op.drop_table("label_presets")
