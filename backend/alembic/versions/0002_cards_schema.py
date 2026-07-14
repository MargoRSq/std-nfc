"""cards schema: categories, templates, cards

Revision ID: 0002_cards_schema
Revises: 0001_init_auth
Create Date: 2026-05-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0002_cards_schema"
down_revision: str | None = "0001_init_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute("""
        CREATE OR REPLACE FUNCTION immutable_unaccent(text)
        RETURNS text AS $$
            SELECT unaccent($1)
        $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    """)

    op.create_table(
        "categories",
        sa.Column("id", sa.SmallInteger(), nullable=False, autoincrement=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name_ru", sa.Text(), nullable=False),
        sa.Column("order_idx", sa.SmallInteger(), nullable=False),
        sa.Column("color_hex", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("code", name="uq_categories_code"),
    )

    op.execute("""
        INSERT INTO categories (code, name_ru, order_idx) VALUES
            ('platinum', 'Платиновые', 1),
            ('gold', 'Золотые', 2),
            ('silver', 'Серебряные', 3),
            ('bronze', 'Бронзовые', 4)
        ON CONFLICT (code) DO NOTHING
    """)

    op.create_table(
        "templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category_id", sa.SmallInteger(), nullable=False),
        sa.Column("default_fields", JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("default_styles", JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("custom_field_schema", JSONB(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
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
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_templates_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_templates_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_templates")),
        sa.UniqueConstraint("name", "category_id", name="uq_templates_name_category_id"),
    )
    op.create_index("ix_templates_category_id", "templates", ["category_id"])

    op.create_table(
        "cards",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("public_slug", sa.Text(), nullable=False),
        sa.Column("category_id", sa.SmallInteger(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("middle_name", sa.Text(), nullable=True),
        sa.Column(
            "full_name_search",
            sa.Text(),
            sa.Computed(
                "immutable_unaccent(lower(coalesce(last_name,'')||' '||coalesce(first_name,'')||' '||coalesce(middle_name,'')))",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("membership_no", sa.Text(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("card_issue_date", sa.Date(), nullable=True),
        sa.Column("join_date", sa.Date(), nullable=True),
        sa.Column("chairman", sa.Text(), nullable=True),
        sa.Column("photo_key", sa.Text(), nullable=True),
        sa.Column(
            "photo_shape",
            sa.Text(),
            server_default=sa.text("'square'"),
            nullable=False,
        ),
        sa.Column("logo_key", sa.Text(), nullable=True),
        sa.Column(
            "bg_kind",
            sa.Text(),
            server_default=sa.text("'solid'"),
            nullable=False,
        ),
        sa.Column("bg_color", sa.Text(), nullable=True),
        sa.Column("bg_gradient", JSONB(), nullable=True),
        sa.Column(
            "custom_fields",
            JSONB(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "label_set",
            JSONB(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("internal_phone", sa.Text(), nullable=True),
        sa.Column("internal_email", sa.Text(), nullable=True),
        sa.Column(
            "feedback_form_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("assigned_admin_id", sa.UUID(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "public_slug ~ '^[A-Za-z0-9_-]{6,32}$'",
            name=op.f("ck_cards_public_slug_format"),
        ),
        sa.CheckConstraint(
            "photo_shape IN ('square', 'circle')",
            name=op.f("ck_cards_photo_shape"),
        ),
        sa.CheckConstraint(
            "bg_kind IN ('solid', 'gradient')",
            name=op.f("ck_cards_bg_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_cards_category_id_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_cards_template_id_templates"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_cards_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_admin_id"],
            ["users.id"],
            name=op.f("fk_cards_assigned_admin_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cards")),
        sa.UniqueConstraint("public_slug", name="uq_cards_public_slug"),
    )

    op.create_index("ix_cards_category_id", "cards", ["category_id"])
    op.create_index("ix_cards_assigned_admin_id", "cards", ["assigned_admin_id"])
    op.create_index("ix_cards_card_issue_date", "cards", ["card_issue_date"])
    op.create_index("ix_cards_join_date", "cards", ["join_date"])
    op.create_index("ix_cards_membership_no", "cards", ["membership_no"])
    op.create_index(
        "ix_cards_full_name_trgm",
        "cards",
        ["full_name_search"],
        postgresql_using="gin",
        postgresql_ops={"full_name_search": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_cards_lower_last_name",
        "cards",
        [sa.text("lower(last_name)")],
    )
    op.create_index(
        "ix_cards_active_deleted",
        "cards",
        ["category_id", "last_name"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_cards_active_deleted", table_name="cards")
    op.drop_index("ix_cards_lower_last_name", table_name="cards")
    op.drop_index("ix_cards_full_name_trgm", table_name="cards")
    op.drop_index("ix_cards_membership_no", table_name="cards")
    op.drop_index("ix_cards_join_date", table_name="cards")
    op.drop_index("ix_cards_card_issue_date", table_name="cards")
    op.drop_index("ix_cards_assigned_admin_id", table_name="cards")
    op.drop_index("ix_cards_category_id", table_name="cards")
    op.drop_table("cards")
    op.drop_index("ix_templates_category_id", table_name="templates")
    op.drop_table("templates")
    op.drop_table("categories")
    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
