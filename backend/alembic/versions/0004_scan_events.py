"""scan_events + scan_aggregates_daily tables

Revision ID: 0004_scan_events
Revises: 0003_import_jobs
Create Date: 2026-05-01

"""

from collections.abc import Sequence
from datetime import date, timedelta

import sqlalchemy as sa
from alembic import op

revision: str = "0004_scan_events"
down_revision: str | None = "0003_import_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE scan_events (
            id          bigserial,
            card_id     uuid NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
            ts          timestamptz NOT NULL DEFAULT now(),
            ip          inet NULL,
            user_agent  text NULL,
            device_type text NULL,
            os_family   text NULL,
            browser_family text NULL,
            country_code text NULL,
            city        text NULL,
            lat         double precision NULL,
            lon         double precision NULL,
            referer     text NULL,
            is_bot      bool NOT NULL DEFAULT false,
            PRIMARY KEY (id, ts)
        ) PARTITION BY RANGE (ts);
    """)

    op.execute("CREATE INDEX ix_scan_events_card_id_ts ON scan_events (card_id, ts DESC);")
    op.execute("CREATE INDEX ix_scan_events_ts_brin ON scan_events USING BRIN (ts);")
    op.execute("CREATE INDEX ix_scan_events_country_ts ON scan_events (country_code, ts);")

    today = date.today().replace(day=1)
    for i in range(3):
        m_start = (today.replace(day=1) + timedelta(days=32 * i)).replace(day=1)
        m_end = (m_start + timedelta(days=32)).replace(day=1)
        partition_name = f"scan_events_{m_start.strftime('%Y_%m')}"
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF scan_events
            FOR VALUES FROM ('{m_start.isoformat()}') TO ('{m_end.isoformat()}');
        """)

    op.create_table(
        "scan_aggregates_daily",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column(
            "card_id",
            sa.UUID(),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("country_code", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("device_type", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("day", "card_id", "country_code", "device_type"),
    )
    op.create_index("ix_scan_aggregates_daily_day", "scan_aggregates_daily", ["day"])


def downgrade() -> None:
    op.drop_index("ix_scan_aggregates_daily_day", table_name="scan_aggregates_daily")
    op.drop_table("scan_aggregates_daily")
    op.execute("DROP TABLE IF EXISTS scan_events CASCADE;")
