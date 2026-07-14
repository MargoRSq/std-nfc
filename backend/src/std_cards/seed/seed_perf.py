"""Fast bulk seeder for performance testing.

Inserts N cards + N scan_events using asyncpg.copy_records_to_table.
Target: <2 min for 100K rows each.

Usage (inside api pod):
    python -m std_cards.seed.seed_perf 100000
"""

import asyncio
import random
import secrets
import sys
import time
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import asyncpg

from std_cards.config import settings

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

LAST_NAMES = [
    "Иванов",
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Васильев",
    "Петров",
    "Соколов",
    "Михайлов",
    "Новиков",
    "Фёдоров",
    "Морозов",
    "Волков",
    "Алексеев",
    "Лебедев",
    "Семёнов",
    "Егоров",
    "Павлов",
    "Козлов",
    "Степанов",
    "Николаев",
    "Орлов",
    "Андреев",
    "Макаров",
    "Никитин",
    "Захаров",
    "Зайцев",
    "Соловьёв",
    "Борисов",
    "Яковлев",
    "Григорьев",
    "Романов",
    "Воробьёв",
    "Сергеев",
    "Кузьмин",
    "Фролов",
    "Александров",
    "Дмитриев",
    "Королёв",
    "Гусев",
    "Киселёв",
    "Ильин",
    "Максимов",
    "Поляков",
    "Сорокин",
    "Виноградов",
    "Ковалёв",
    "Белов",
    "Медведев",
    "Антонов",
    "Тарасов",
]
FIRST_NAMES = [
    "Александр",
    "Дмитрий",
    "Максим",
    "Сергей",
    "Андрей",
    "Алексей",
    "Артём",
    "Илья",
    "Кирилл",
    "Михаил",
    "Никита",
    "Матвей",
    "Роман",
    "Егор",
    "Арсений",
    "Иван",
    "Денис",
    "Евгений",
    "Тимофей",
    "Владислав",
    "Игорь",
    "Владимир",
    "Павел",
    "Руслан",
    "Марк",
    "Константин",
    "Тимур",
    "Олег",
    "Ярослав",
    "Антон",
    "Анна",
    "Мария",
    "Елена",
    "Дарья",
    "Алина",
    "Ирина",
    "Ксения",
    "Анастасия",
    "Виктория",
    "Полина",
    "Юлия",
    "Софья",
    "Татьяна",
    "Ольга",
    "Вероника",
]
MIDDLE_NAMES = [
    "Александрович",
    "Дмитриевич",
    "Сергеевич",
    "Андреевич",
    "Алексеевич",
    "Иванович",
    "Михайлович",
    "Викторович",
    "Николаевич",
    "Юрьевич",
    "Игоревич",
    "Александровна",
    "Дмитриевна",
    "Сергеевна",
    "Андреевна",
    "Алексеевна",
    "Ивановна",
    "Михайловна",
    "Викторовна",
    "Николаевна",
    "Юрьевна",
    "Игоревна",
]


def hex_color() -> str:
    return f"#{random.randint(0, 0xFFFFFF):06x}"


def random_date(start_year: int, end_year: int) -> date:
    start = date(start_year, 1, 1).toordinal()
    end = date(end_year, 12, 31).toordinal()
    return date.fromordinal(random.randint(start, end))


REGIONS = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Челябинск",
    "Самара",
    "Омск",
    "Ростов-на-Дону",
    "Уфа",
    "Красноярск",
    "Воронеж",
    "Пермь",
    "Волгоград",
    "Краснодар",
    "Саратов",
    "Тюмень",
    "Тольятти",
    "Ижевск",
]

COUNTRIES = ["RU", "BY", "KZ", "UA", "DE", "US"]
CITIES = ["Moscow", "Saint Petersburg", "Minsk", "Almaty", "Berlin"]
DEVICES = ["mobile", "tablet", "desktop"]
OS_FAMILIES = ["iOS", "Android", "Windows", "macOS", "Linux"]
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge", "Yandex"]


def gen_slug(n: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def asyncpg_dsn() -> str:
    """Convert sqlalchemy DSN to plain asyncpg DSN."""
    url = settings.effective_db_url
    return url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg://", "postgresql://"
    )


async def get_admin_id(conn: asyncpg.Connection) -> UUID:
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE email=$1",
        settings.SEED.SUPER_ADMIN_EMAIL,
    )
    if row is None:
        raise RuntimeError("Run seed.py first — no super admin found")
    return row["id"]


async def get_existing_slugs(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT public_slug FROM cards")
    return {r["public_slug"] for r in rows}


def make_card_record(admin_id: UUID, slug: str) -> tuple:
    issue_date = random_date(2024, 2026)
    join_date = random_date(2015, 2023)
    return (
        slug,
        random.randint(1, 4),
        random.choice(LAST_NAMES),
        random.choice(FIRST_NAMES),
        random.choice(MIDDLE_NAMES) if random.random() < 0.9 else None,
        str(random.randint(1000, 999999)),
        issue_date,
        join_date,
        random.choice(REGIONS),
        "solid",
        hex_color(),
        admin_id,
    )


async def seed_cards(conn: asyncpg.Connection, count: int) -> list[UUID]:
    print(f"[cards] Generating {count} card records...")
    t0 = time.monotonic()

    existing = await get_existing_slugs(conn)
    print(f"[cards] Found {len(existing)} existing slugs")

    admin_id = await get_admin_id(conn)
    print(f"[cards] Admin id: {admin_id}")

    records: list[tuple] = []
    used_slugs: set[str] = set()
    for _ in range(count):
        while True:
            slug = gen_slug(7)
            if slug not in existing and slug not in used_slugs:
                used_slugs.add(slug)
                break
        records.append(make_card_record(admin_id, slug))

    print(f"[cards] Generated in {time.monotonic() - t0:.1f}s, inserting in batches of 5000...")

    BATCH = 5000
    total_inserted = 0
    new_card_ids: list[UUID] = []
    for batch_start in range(0, len(records), BATCH):
        batch = records[batch_start : batch_start + BATCH]
        async with conn.transaction():
            rows = await conn.fetch(
                """
                INSERT INTO cards (
                    public_slug, category_id, last_name, first_name, middle_name,
                    membership_no, card_issue_date, join_date, region,
                    bg_kind, bg_color, created_by
                )
                SELECT * FROM unnest(
                    $1::text[], $2::smallint[], $3::text[], $4::text[], $5::text[],
                    $6::text[], $7::date[], $8::date[], $9::text[],
                    $10::text[], $11::text[], $12::uuid[]
                )
                RETURNING id
                """,
                [r[0] for r in batch],
                [r[1] for r in batch],
                [r[2] for r in batch],
                [r[3] for r in batch],
                [r[4] for r in batch],
                [r[5] for r in batch],
                [r[6] for r in batch],
                [r[7] for r in batch],
                [r[8] for r in batch],
                [r[9] for r in batch],
                [r[10] for r in batch],
                [r[11] for r in batch],
            )
            new_card_ids.extend(r["id"] for r in rows)
        total_inserted += len(batch)
        if total_inserted % 10000 == 0 or total_inserted == count:
            print(f"[cards] Inserted {total_inserted}/{count} ({time.monotonic() - t0:.1f}s)")

    print(f"[cards] Done in {time.monotonic() - t0:.1f}s")
    return new_card_ids


async def get_partition_window(conn: asyncpg.Connection) -> tuple[datetime, datetime]:
    """Get min/max ts from existing scan_events partitions."""
    row = await conn.fetchrow(
        """
        SELECT
            MIN(pg_get_expr(c.relpartbound, c.oid)) AS partitions
        FROM pg_class c
        WHERE c.relispartition AND c.relname LIKE 'scan_events%'
        """
    )
    del row
    return (
        datetime(2026, 5, 1, tzinfo=UTC),
        datetime(2026, 7, 31, 23, 59, 59, tzinfo=UTC),
    )


async def seed_scans(conn: asyncpg.Connection, count: int, card_ids: list[UUID]) -> None:
    print(f"[scans] Generating {count} scan_event records...")
    t0 = time.monotonic()

    if not card_ids:
        rows = await conn.fetch(
            "SELECT id FROM cards WHERE deleted_at IS NULL ORDER BY random() LIMIT 50000"
        )
        card_ids = [r["id"] for r in rows]
        print(f"[scans] Sampled {len(card_ids)} card_ids from existing cards")

    start_ts, end_ts = await get_partition_window(conn)
    span_seconds = int((end_ts - start_ts).total_seconds())
    print(f"[scans] Window: {start_ts} -> {end_ts} ({span_seconds}s)")

    BATCH = 5000
    total = 0
    for batch_start in range(0, count, BATCH):
        batch_size = min(BATCH, count - batch_start)
        records = []
        for _ in range(batch_size):
            ts = start_ts + timedelta(seconds=random.randint(0, span_seconds))
            country = random.choice(COUNTRIES)
            city = random.choice(CITIES) if random.random() < 0.85 else None
            records.append(
                (
                    random.choice(card_ids),
                    ts,
                    f"203.0.113.{random.randint(1, 254)}",
                    "Mozilla/5.0 perf-test",
                    random.choice(DEVICES),
                    random.choice(OS_FAMILIES),
                    random.choice(BROWSERS),
                    country,
                    city,
                    None,
                    None,
                    None,
                    random.random() < 0.05,
                )
            )
        async with conn.transaction():
            await conn.executemany(
                """
                INSERT INTO scan_events (
                    card_id, ts, ip, user_agent, device_type,
                    os_family, browser_family, country_code, city,
                    lat, lon, referer, is_bot
                ) VALUES ($1, $2, $3::inet, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                records,
            )
        total += batch_size
        if total % 10000 == 0 or total == count:
            print(f"[scans] Inserted {total}/{count} ({time.monotonic() - t0:.1f}s)")

    print(f"[scans] Done in {time.monotonic() - t0:.1f}s")


async def main_async(count: int) -> None:
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("seed_perf refused: ENVIRONMENT=production")
    dsn = asyncpg_dsn()
    print(f"[main] Connecting to: {dsn.split('@')[-1]}")
    conn = await asyncpg.connect(dsn)
    try:
        new_card_ids = await seed_cards(conn, count)
        await seed_scans(conn, count, new_card_ids)
        print("[main] Verifying counts...")
        c_cards = await conn.fetchval("SELECT COUNT(*) FROM cards")
        c_scans = await conn.fetchval("SELECT COUNT(*) FROM scan_events")
        print(f"[main] cards={c_cards}, scan_events={c_scans}")
    finally:
        await conn.close()


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    asyncio.run(main_async(count))


if __name__ == "__main__":
    main()
