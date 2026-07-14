"""users.name — admin display name

Revision ID: 0020_user_name
Revises: 0019_user_last_totp_step
Create Date: 2026-06-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_user_name"
down_revision: str | None = "0019_user_last_totp_step"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "name")
