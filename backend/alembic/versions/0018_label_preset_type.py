"""label_presets.type column

Revision ID: 0018_label_preset_type
Revises: 0017_label_presets
Create Date: 2026-05-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_label_preset_type"
down_revision: str | None = "0017_label_presets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VALID_TYPES = ("text", "number", "date", "url", "phone", "email")


def upgrade() -> None:
    op.add_column(
        "label_presets",
        sa.Column(
            "type",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'text'"),
        ),
    )
    op.create_check_constraint(
        "ck_label_presets_type",
        "label_presets",
        sa.text(
            "type IN ('text', 'number', 'date', 'url', 'phone', 'email')",
        ),
    )


def downgrade() -> None:
    op.drop_constraint("ck_label_presets_type", "label_presets", type_="check")
    op.drop_column("label_presets", "type")
