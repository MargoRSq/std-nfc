"""feedback_messages table

Revision ID: 0006_feedback_messages
Revises: 0005_acl_audit
Create Date: 2026-05-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_feedback_messages"
down_revision: str | None = "0005_acl_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback_messages",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "card_id",
            sa.UUID(),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("contact", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_feedback_messages_card_id", "feedback_messages", ["card_id"])
    op.create_index("ix_feedback_messages_created_at", "feedback_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_feedback_messages_created_at", table_name="feedback_messages")
    op.drop_index("ix_feedback_messages_card_id", table_name="feedback_messages")
    op.drop_table("feedback_messages")
