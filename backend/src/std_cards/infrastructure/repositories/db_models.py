"""SQLAlchemy Core table definitions.

Все таблицы регистрируются в `metadata` через `StdCardsTable` фабрику
(автоматически добавляет created_at/updated_at + индексы).
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, INET, JSONB, UUID

from std_cards.db.base import StdCardsTable, metadata

__all__ = [
    "metadata",
    "users",
    "refresh_tokens",
    "login_challenges",
    "password_resets",
    "categories",
    "templates",
    "cards",
    "import_jobs",
    "admin_card_groups",
    "audit_log",
    "feedback_messages",
    "card_messages",
    "scan_events",
    "scan_aggregates_daily",
    "label_presets",
]


users = StdCardsTable(
    "users",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column("email", CITEXT(), nullable=False, doc="Email админа"),
    sa.Column("name", sa.Text(), nullable=True, doc="ФИО админа (display)"),
    sa.Column("password_hash", sa.Text(), nullable=False, doc="bcrypt hash"),
    sa.Column("totp_secret", sa.Text(), nullable=True, doc="base32 секрет TOTP"),
    sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("recovery_codes", ARRAY(sa.Text()), nullable=True, doc="bcrypt-хеши recovery кодов"),
    sa.Column(
        "role",
        sa.Text(),
        nullable=False,
        server_default=sa.text("'admin'"),
        doc="super_admin|admin",
    ),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
    sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column(
        "token_version",
        sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
        doc="Инкремент = форс-логаут всех сессий",
    ),
    sa.Column(
        "last_totp_step",
        sa.BigInteger(),
        nullable=True,
        doc="period index последнего принятого TOTP-кода — replay guard",
    ),
    sa.UniqueConstraint("email", name="uq_users_email"),
    sa.CheckConstraint("role IN ('super_admin', 'admin')", name="role_value"),
)


refresh_tokens = StdCardsTable(
    "refresh_tokens",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column(
        "user_id",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("token_hash", sa.Text(), nullable=False, doc="SHA-256 hex от opaque refresh token"),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column(
        "replaced_by_id",
        UUID(as_uuid=True),
        sa.ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("family_id", UUID(as_uuid=True), nullable=False),
    sa.Column("user_agent", sa.Text(), nullable=True),
    sa.Column("ip", INET(), nullable=True),
    sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    sa.Index("ix_refresh_tokens_user_id_expires", "user_id", "expires_at"),
    sa.Index(
        "ix_refresh_tokens_user_active",
        "user_id",
        "expires_at",
        postgresql_where=sa.text("revoked_at IS NULL"),
    ),
    sa.Index("ix_refresh_tokens_family_id", "family_id"),
)


login_challenges = StdCardsTable(
    "login_challenges",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column(
        "user_id",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("challenge_hash", sa.Text(), nullable=False, doc="SHA-256 от challenge_token"),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("ip", INET(), nullable=True),
    sa.UniqueConstraint("challenge_hash", name="uq_login_challenges_challenge_hash"),
    sa.Index("ix_login_challenges_user_id", "user_id"),
    sa.Index("ix_login_challenges_expires_at", "expires_at"),
    add_timestamp_indexes=False,
)


password_resets = StdCardsTable(
    "password_resets",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column(
        "user_id",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("token_hash", sa.Text(), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    sa.UniqueConstraint("token_hash", name="uq_password_resets_token_hash"),
    sa.Index("ix_password_resets_user_id", "user_id"),
    add_timestamp_indexes=False,
)


categories = StdCardsTable(
    "categories",
    metadata,
    sa.Column("id", sa.SmallInteger(), primary_key=True, autoincrement=True),
    sa.Column("code", sa.Text(), nullable=False),
    sa.Column("name_ru", sa.Text(), nullable=False),
    sa.Column("order_idx", sa.SmallInteger(), nullable=False),
    sa.Column("color_hex", sa.Text(), nullable=True),
    sa.UniqueConstraint("code", name="uq_categories_code"),
    add_timestamp_indexes=False,
)


templates = StdCardsTable(
    "templates",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column("name", sa.Text(), nullable=False),
    sa.Column(
        "category_id",
        sa.SmallInteger(),
        sa.ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    sa.Column("default_fields", JSONB(), nullable=False, server_default=sa.text("'{}'")),
    sa.Column("default_styles", JSONB(), nullable=False, server_default=sa.text("'{}'")),
    sa.Column("custom_field_schema", JSONB(), nullable=False, server_default=sa.text("'[]'")),
    sa.Column(
        "created_by",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    sa.UniqueConstraint("name", "category_id", name="uq_templates_name_category_id"),
    sa.Index("ix_templates_category_id", "category_id"),
    sa.Index(
        "uq_templates_one_default",
        "is_default",
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    ),
    add_timestamp_indexes=False,
)


import_jobs = StdCardsTable(
    "import_jobs",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column(
        "created_by",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column(
        "template_id",
        UUID(as_uuid=True),
        sa.ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("file_key", sa.Text(), nullable=False),
    sa.Column("file_name", sa.Text(), nullable=False),
    sa.Column(
        "status",
        sa.Text(),
        nullable=False,
        server_default=sa.text("'pending'"),
    ),
    sa.Column("total_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
    sa.Column("processed_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
    sa.Column("inserted_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
    sa.Column("error_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    sa.Column(
        "errors_sample",
        JSONB(),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    ),
    sa.Column("errors_file_key", sa.Text(), nullable=True),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    ),
    sa.CheckConstraint(
        "status IN ('pending','running','succeeded','failed','cancelled')",
        name="ck_import_jobs_status",
    ),
    sa.Index("ix_import_jobs_created_by_created_at", "created_by", "created_at"),
    sa.Index("ix_import_jobs_status", "status"),
    add_timestamps=False,
    add_timestamp_indexes=False,
)


cards = StdCardsTable(
    "cards",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column("public_slug", sa.Text(), nullable=False),
    sa.Column(
        "category_id",
        sa.SmallInteger(),
        sa.ForeignKey("categories.id"),
        nullable=False,
    ),
    sa.Column(
        "template_id",
        UUID(as_uuid=True),
        sa.ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
    ),
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
    sa.Column("photo_shape", sa.Text(), nullable=False, server_default=sa.text("'square'")),
    sa.Column("logo_key", sa.Text(), nullable=True),
    sa.Column("logo_shape", sa.Text(), nullable=False, server_default=sa.text("'square'")),
    sa.Column("bg_kind", sa.Text(), nullable=False, server_default=sa.text("'solid'")),
    sa.Column("bg_color", sa.Text(), nullable=True),
    sa.Column("bg_gradient", JSONB(), nullable=True),
    sa.Column("avatar_color", sa.Text(), nullable=True),
    sa.Column("avatar_gradient", JSONB(), nullable=True),
    sa.Column("custom_fields", JSONB(), nullable=False, server_default=sa.text("'{}'")),
    sa.Column("label_set", JSONB(), nullable=False, server_default=sa.text("'[]'")),
    sa.Column("field_order", JSONB(), nullable=False, server_default=sa.text("'[]'")),
    sa.Column("field_labels", JSONB(), nullable=False, server_default=sa.text("'{}'")),
    sa.Column("contacts", JSONB(), nullable=False, server_default=sa.text("'[]'")),
    sa.Column("internal_blocks", JSONB(), nullable=False, server_default=sa.text("'[]'")),
    sa.Column("hide_birth_date", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("hide_region", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("hide_card_issue_date", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("hide_join_date", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("hide_chairman", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("feedback_form_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column(
        "created_by",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column(
        "assigned_admin_id",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("public_slug ~ '^[A-Za-z0-9_-]{6,32}$'", name="ck_cards_public_slug_format"),
    sa.CheckConstraint("photo_shape IN ('square', 'circle')", name="ck_cards_photo_shape"),
    sa.CheckConstraint(
        "logo_shape IN ('square', 'circle', 'rectangle')", name="ck_cards_logo_shape"
    ),
    sa.CheckConstraint("bg_kind IN ('solid', 'gradient')", name="ck_cards_bg_kind"),
    sa.UniqueConstraint("public_slug", name="uq_cards_public_slug"),
    sa.Index("ix_cards_category_id", "category_id"),
    sa.Index("ix_cards_assigned_admin_id", "assigned_admin_id"),
    sa.Index("ix_cards_card_issue_date", "card_issue_date"),
    sa.Index("ix_cards_join_date", "join_date"),
    sa.Index("ix_cards_membership_no", "membership_no"),
    sa.Index(
        "uq_cards_membership_no_active",
        sa.func.lower(sa.func.btrim(sa.text("membership_no"))),
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    ),
    add_timestamp_indexes=False,
)


admin_card_groups = sa.Table(
    "admin_card_groups",
    metadata,
    sa.Column(
        "user_id",
        UUID(as_uuid=True),
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
        server_default=sa.func.now(),
    ),
    sa.PrimaryKeyConstraint("user_id", "category_id", name="pk_admin_card_groups"),
    sa.Index("ix_admin_card_groups_user_id", "user_id"),
)


audit_log = sa.Table(
    "audit_log",
    metadata,
    sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True, autoincrement=True),
    sa.Column(
        "ts",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column(
        "actor_id",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("actor_email", sa.Text(), nullable=True),
    sa.Column("action", sa.Text(), nullable=False),
    sa.Column("entity_type", sa.Text(), nullable=True),
    sa.Column("entity_id", sa.Text(), nullable=True),
    sa.Column("ip", INET(), nullable=True),
    sa.Column("user_agent", sa.Text(), nullable=True),
    sa.Column("diff", JSONB(), nullable=True),
    sa.Index("ix_audit_log_actor_id_ts", "actor_id", "ts"),
    sa.Index("ix_audit_log_entity", "entity_type", "entity_id", "ts"),
)


scan_events = sa.Table(
    "scan_events",
    metadata,
    sa.Column("id", sa.BigInteger(), nullable=False),
    sa.Column("card_id", UUID(as_uuid=True), nullable=False),
    sa.Column(
        "ts",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("ip", INET(), nullable=True),
    sa.Column("user_agent", sa.Text(), nullable=True),
    sa.Column("device_type", sa.Text(), nullable=True),
    sa.Column("os_family", sa.Text(), nullable=True),
    sa.Column("browser_family", sa.Text(), nullable=True),
    sa.Column("country_code", sa.Text(), nullable=True),
    sa.Column("city", sa.Text(), nullable=True),
    sa.Column("lat", sa.Float(), nullable=True),
    sa.Column("lon", sa.Float(), nullable=True),
    sa.Column("referer", sa.Text(), nullable=True),
    sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    sa.PrimaryKeyConstraint("id", "ts", name="pk_scan_events"),
)


feedback_messages = sa.Table(
    "feedback_messages",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column(
        "card_id",
        UUID(as_uuid=True),
        sa.ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("name", sa.Text(), nullable=False),
    sa.Column("contact", sa.Text(), nullable=False),
    sa.Column("message", sa.Text(), nullable=False),
    sa.Column("ip", INET(), nullable=True),
    sa.Column("user_agent", sa.Text(), nullable=True),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    sa.Index("ix_feedback_messages_card_id", "card_id"),
    sa.Index("ix_feedback_messages_created_at", "created_at"),
)


card_messages = sa.Table(
    "card_messages",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column(
        "card_id",
        UUID(as_uuid=True),
        sa.ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("image_key", sa.Text(), nullable=True),
    sa.Column(
        "created_by",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    ),
    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint(
        "char_length(text) <= 2000",
        name="ck_card_messages_text_length",
    ),
    sa.Index(
        "ix_card_messages_card_active",
        "card_id",
        postgresql_where=sa.text("deleted_at IS NULL"),
    ),
    sa.Index("ix_card_messages_card_created", "card_id", sa.text("created_at DESC")),
)


scan_aggregates_daily = sa.Table(
    "scan_aggregates_daily",
    metadata,
    sa.Column("day", sa.Date(), nullable=False),
    sa.Column("card_id", UUID(as_uuid=True), nullable=False),
    sa.Column("country_code", sa.Text(), nullable=False, server_default=sa.text("''")),
    sa.Column("device_type", sa.Text(), nullable=False, server_default=sa.text("''")),
    sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    sa.PrimaryKeyConstraint(
        "day", "card_id", "country_code", "device_type", name="pk_scan_aggregates_daily"
    ),
    sa.Index("ix_scan_aggregates_daily_day", "day"),
)


label_presets = StdCardsTable(
    "label_presets",
    metadata,
    sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    ),
    sa.Column(
        "admin_id",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("name", sa.String(length=100), nullable=False),
    sa.Column("order_idx", sa.Integer(), nullable=False, server_default=sa.text("0")),
    sa.Column(
        "type",
        sa.String(length=16),
        nullable=False,
        server_default=sa.text("'text'"),
    ),
    sa.UniqueConstraint("admin_id", "name", name="uq_label_presets_admin_name"),
    sa.Index("ix_label_presets_admin_order", "admin_id", "order_idx"),
)
