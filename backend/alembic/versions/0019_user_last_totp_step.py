"""users.last_totp_step — TOTP replay guard

Revision ID: 0019_user_last_totp_step
Revises: 0018_label_preset_type
Create Date: 2026-06-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_user_last_totp_step"
down_revision: str | None = "0018_label_preset_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_totp_step", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_totp_step")
