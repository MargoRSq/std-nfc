"""init: extensions, users, refresh_tokens, login_challenges, password_resets

Revision ID: 0001_init_auth
Revises:
Create Date: 2026-05-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init_auth"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("totp_secret", sa.Text(), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recovery_codes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("role", sa.Text(), server_default=sa.text("'admin'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('super_admin', 'admin')", name=op.f("ck_users_role_value")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("users_created_at_idx", "users", ["created_at"], unique=False)
    op.create_index("users_updated_at_idx", "users", ["updated_at"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.UUID(), nullable=True),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"],
            ["refresh_tokens.id"],
            name=op.f("fk_refresh_tokens_replaced_by_id_refresh_tokens"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index(
        "ix_refresh_tokens_user_id_expires",
        "refresh_tokens",
        ["user_id", "expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_refresh_tokens_user_active",
        "refresh_tokens",
        ["user_id", "expires_at"],
        unique=False,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("refresh_tokens_created_at_idx", "refresh_tokens", ["created_at"], unique=False)
    op.create_index("refresh_tokens_updated_at_idx", "refresh_tokens", ["updated_at"], unique=False)

    op.create_table(
        "login_challenges",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("challenge_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_login_challenges_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_challenges")),
        sa.UniqueConstraint("challenge_hash", name="uq_login_challenges_challenge_hash"),
    )
    op.create_index("ix_login_challenges_user_id", "login_challenges", ["user_id"])
    op.create_index("ix_login_challenges_expires_at", "login_challenges", ["expires_at"])

    op.create_table(
        "password_resets",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_password_resets_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_resets")),
        sa.UniqueConstraint("token_hash", name="uq_password_resets_token_hash"),
    )
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_password_resets_user_id", table_name="password_resets")
    op.drop_table("password_resets")
    op.drop_index("ix_login_challenges_expires_at", table_name="login_challenges")
    op.drop_index("ix_login_challenges_user_id", table_name="login_challenges")
    op.drop_table("login_challenges")
    op.drop_index("refresh_tokens_updated_at_idx", table_name="refresh_tokens")
    op.drop_index("refresh_tokens_created_at_idx", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens", if_exists=True)
    op.drop_index("ix_refresh_tokens_user_active", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id_expires", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("users_updated_at_idx", table_name="users")
    op.drop_index("users_created_at_idx", table_name="users")
    op.drop_table("users")
