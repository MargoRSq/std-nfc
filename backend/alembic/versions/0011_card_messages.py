"""card_messages table + cards.last_opened_at column

Revision ID: 0011_card_messages
Revises: 0010_tpl_is_default
Create Date: 2026-05-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_card_messages"
down_revision: str | None = "0010_tpl_is_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "card_messages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "card_id",
            sa.UUID(),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("image_key", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(text) <= 2000",
            name="ck_card_messages_text_length",
        ),
    )
    op.create_index(
        "ix_card_messages_card_active",
        "card_messages",
        ["card_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_card_messages_card_created",
        "card_messages",
        ["card_id", sa.text("created_at DESC")],
    )

    op.add_column(
        "cards",
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cards", "last_opened_at")
    op.drop_index("ix_card_messages_card_created", table_name="card_messages")
    op.drop_index("ix_card_messages_card_active", table_name="card_messages")
    op.drop_table("card_messages")
