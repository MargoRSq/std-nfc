"""dedup membership_no and add unique partial index

Revision ID: 0016_membership_no_unique
Revises: 0015_field_order
Create Date: 2026-05-20

Renames active duplicates (deleted_at IS NULL) by appending "-dup{N}" suffix
based on created_at order (oldest keeps original), then adds a partial unique
index on lower(trim(membership_no)) WHERE deleted_at IS NULL.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016_membership_no_unique"
down_revision: str | None = "0015_field_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                membership_no,
                ROW_NUMBER() OVER (
                    PARTITION BY lower(btrim(membership_no))
                    ORDER BY created_at ASC, id ASC
                ) AS rn
            FROM cards
            WHERE deleted_at IS NULL
        )
        UPDATE cards c
        SET membership_no = ranked.membership_no || '-dup' || (ranked.rn - 1)::text,
            updated_at = now()
        FROM ranked
        WHERE c.id = ranked.id AND ranked.rn > 1
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_cards_membership_no_active
        ON cards (lower(btrim(membership_no)))
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_cards_membership_no_active")
