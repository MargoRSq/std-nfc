import asyncio
import random
import sys

from faker import Faker

from std_cards.config import settings
from std_cards.core.slug import gen_slug
from std_cards.db.session import get_session_maker
from std_cards.infrastructure.repositories import CardRepository, UserRepository
from std_cards.models.card import CardCreate

fake = Faker("ru_RU")


async def seed_cards(count: int = 5000) -> None:
    sm = get_session_maker()
    user_repo = UserRepository(sm)
    card_repo = CardRepository(sm)

    admin = await user_repo.get_by_email(settings.SEED.SUPER_ADMIN_EMAIL)
    if admin is None:
        raise RuntimeError("Run seed.py first")

    BATCH = 100
    for batch_start in range(0, count, BATCH):
        for _ in range(BATCH):
            full_name = fake.name().split()
            await card_repo.create(
                CardCreate(
                    last_name=full_name[0] if full_name else "Иванов",
                    first_name=full_name[1] if len(full_name) > 1 else "Иван",
                    membership_no=str(random.randint(1000, 99999)),
                    category_id=random.randint(1, 4),
                    region=fake.city(),
                    card_issue_date=fake.date_between(start_date="-2y", end_date="today"),
                    join_date=fake.date_between(start_date="-10y", end_date="-2y"),
                    bg_kind="solid",
                    bg_color=fake.hex_color(),
                ),
                slug=gen_slug(7),
                created_by=admin.id,
            )
        print(f"Inserted {batch_start + BATCH} / {count}")


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    asyncio.run(seed_cards(count))


if __name__ == "__main__":
    main()
