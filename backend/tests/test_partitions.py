from datetime import date, timedelta

import sqlalchemy as sa

from std_cards.db.partitions import ensure_next_month, ensure_partition_for_month


async def test_ensure_partition_creates_table(session_maker):
    target = date.today().replace(day=1) + timedelta(days=95)
    target = target.replace(day=1)
    partition_name = f"scan_events_{target.strftime('%Y_%m')}"

    async with session_maker.session() as conn:
        await ensure_partition_for_month(conn, target)

        result = await conn.execute(
            sa.text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = :name"
            ).bindparams(name=partition_name)
        )
        row = result.fetchone()

    assert row is not None, f"Partition {partition_name} was not created"


async def test_ensure_next_month_idempotent(session_maker):
    async with session_maker.session() as conn:
        await ensure_next_month(conn)
        await ensure_next_month(conn)


async def test_ensure_partition_for_specific_month(session_maker):
    target = date(2030, 6, 15)
    partition_name = "scan_events_2030_06"

    async with session_maker.session() as conn:
        await ensure_partition_for_month(conn, target)

        result = await conn.execute(
            sa.text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = :name"
            ).bindparams(name=partition_name)
        )
        row = result.fetchone()

    assert row is not None
