"""import_jobs table

Revision ID: 0003_import_jobs
Revises: 0002_cards_schema
Create Date: 2026-05-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_import_jobs"
down_revision: str | None = "0002_cards_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("template_id", sa.UUID(), nullable=True),
        sa.Column("file_key", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "total_rows",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "processed_rows",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "inserted_rows",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "error_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "errors_sample",
            JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("errors_file_key", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('pending','running','succeeded','failed','cancelled')",
            name="ck_import_jobs_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_import_jobs_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_import_jobs_template_id_templates"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(
        "ix_import_jobs_created_by_created_at",
        "import_jobs",
        ["created_by", "created_at"],
    )
    op.create_index("ix_import_jobs_status", "import_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_import_jobs_status", table_name="import_jobs")
    op.drop_index("ix_import_jobs_created_by_created_at", table_name="import_jobs")
    op.drop_table("import_jobs")
