"""admin_card_groups + audit_log tables

Revision ID: 0005_acl_audit
Revises: 0004_scan_events
Create Date: 2026-05-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_acl_audit"
down_revision: str | None = "0004_scan_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_card_groups",
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.SmallInteger(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("can_edit", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("can_export", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "category_id"),
    )
    op.create_index("ix_admin_card_groups_user_id", "admin_card_groups", ["user_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "actor_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_email", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("diff", postgresql.JSONB(), nullable=True),
    )
    op.execute("CREATE INDEX ix_audit_log_ts ON audit_log USING BRIN (ts);")
    op.create_index("ix_audit_log_actor_id_ts", "audit_log", ["actor_id", "ts"])
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id", "ts"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id_ts", table_name="audit_log")
    op.execute("DROP INDEX IF EXISTS ix_audit_log_ts;")
    op.drop_table("audit_log")
    op.drop_index("ix_admin_card_groups_user_id", table_name="admin_card_groups")
    op.drop_table("admin_card_groups")
