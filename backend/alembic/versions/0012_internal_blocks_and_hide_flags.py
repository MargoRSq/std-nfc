"""internal_blocks JSONB + hide_* flags for preset rows

Revision ID: 0012_internal_blocks
Revises: 0011_card_messages
Create Date: 2026-05-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0012_internal_blocks"
down_revision: str | None = "0011_card_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column(
            "internal_blocks",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    for col in (
        "hide_birth_date",
        "hide_region",
        "hide_card_issue_date",
        "hide_join_date",
        "hide_chairman",
    ):
        op.add_column(
            "cards",
            sa.Column(col, sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    op.execute(
        """
        UPDATE cards SET internal_blocks =
            CASE WHEN internal_phone IS NOT NULL AND internal_phone <> ''
                 THEN jsonb_build_array(jsonb_build_object('type','phone','value',internal_phone,'is_internal',true))
                 ELSE '[]'::jsonb END
          ||
            CASE WHEN internal_email IS NOT NULL AND internal_email <> ''
                 THEN jsonb_build_array(jsonb_build_object('type','email','value',internal_email,'is_internal',true))
                 ELSE '[]'::jsonb END
          ||
            CASE WHEN internal_notes IS NOT NULL AND internal_notes <> ''
                 THEN jsonb_build_array(jsonb_build_object('type','notes','value',internal_notes,'is_internal',true,'is_hidden',true))
                 ELSE '[]'::jsonb END
        """
    )

    op.drop_column("cards", "internal_phone")
    op.drop_column("cards", "internal_email")
    op.drop_column("cards", "internal_notes")


def downgrade() -> None:
    op.add_column("cards", sa.Column("internal_phone", sa.Text(), nullable=True))
    op.add_column("cards", sa.Column("internal_email", sa.Text(), nullable=True))
    op.add_column("cards", sa.Column("internal_notes", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE cards SET
            internal_phone = (
                SELECT value FROM jsonb_to_recordset(internal_blocks) AS x(type text, value text)
                WHERE type = 'phone' LIMIT 1
            ),
            internal_email = (
                SELECT value FROM jsonb_to_recordset(internal_blocks) AS x(type text, value text)
                WHERE type = 'email' LIMIT 1
            ),
            internal_notes = (
                SELECT value FROM jsonb_to_recordset(internal_blocks) AS x(type text, value text)
                WHERE type = 'notes' LIMIT 1
            )
        """
    )

    op.drop_column("cards", "hide_birth_date")
    op.drop_column("cards", "hide_region")
    op.drop_column("cards", "hide_card_issue_date")
    op.drop_column("cards", "hide_join_date")
    op.drop_column("cards", "hide_chairman")
    op.drop_column("cards", "internal_blocks")
