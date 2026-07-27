"""Сброс данных аналитики: счётчики сканирований начинают считаться с нуля.

Чистит `scan_events` (со всеми партициями), дневные агрегаты и отметку
last_opened_at у карточек. Карточки, пользователи и сообщения не трогаются.

Запуск:
    python -m std_cards.scripts.reset_analytics --yes
"""

import argparse
import asyncio
import logging

import sqlalchemy as sa

from std_cards.db.session import get_session_maker

logger = logging.getLogger(__name__)

STATEMENTS = (
    "TRUNCATE TABLE scan_events",
    "TRUNCATE TABLE scan_aggregates_daily",
    "UPDATE cards SET last_opened_at = NULL WHERE last_opened_at IS NOT NULL",
)


async def reset_analytics() -> None:
    sm = get_session_maker()
    async with sm.session() as conn:
        for statement in STATEMENTS:
            result = await conn.execute(sa.text(statement))
            logger.info("%s → %s rows", statement, result.rowcount)


def main() -> None:
    parser = argparse.ArgumentParser(description="Удалить все данные аналитики сканирований")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="подтверждение: данные сканирований будут удалены безвозвратно",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not args.yes:
        parser.error("нужен флаг --yes: операция удаляет все скан-события без возможности отката")
    asyncio.run(reset_analytics())
    logger.info("Аналитика очищена")


if __name__ == "__main__":
    main()
