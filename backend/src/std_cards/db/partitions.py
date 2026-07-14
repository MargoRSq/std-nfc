import logging
from datetime import date, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)


async def ensure_partition_for_month(conn: AsyncConnection, target: date) -> None:
    m_start = target.replace(day=1)
    m_end = (m_start + timedelta(days=32)).replace(day=1)
    partition_name = f"scan_events_{m_start.strftime('%Y_%m')}"
    sql = f"""
        CREATE TABLE IF NOT EXISTS {partition_name}
        PARTITION OF scan_events
        FOR VALUES FROM ('{m_start.isoformat()}') TO ('{m_end.isoformat()}');
    """
    await conn.execute(sa.text(sql))
    logger.info("Ensured partition: %s", partition_name)


async def ensure_next_month(conn: AsyncConnection) -> None:
    today = date.today()
    next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    await ensure_partition_for_month(conn, next_month)


async def ensure_upcoming_partitions(conn: AsyncConnection, months_ahead: int = 3) -> None:
    """Ensure scan_events partitions exist for the current month and the next
    ``months_ahead`` months, so inserts never hit a missing partition. Safe to
    re-run (CREATE TABLE IF NOT EXISTS); self-heals a deploy that lagged behind."""
    cursor = date.today().replace(day=1)
    for _ in range(months_ahead + 1):
        await ensure_partition_for_month(conn, cursor)
        cursor = (cursor + timedelta(days=32)).replace(day=1)
