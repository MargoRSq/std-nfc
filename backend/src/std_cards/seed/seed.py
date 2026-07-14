import asyncio
import logging

import sqlalchemy as sa

from std_cards.config import settings
from std_cards.core.security import hash_password
from std_cards.db.session import get_session_maker
from std_cards.infrastructure.repositories import UserRepository
from std_cards.infrastructure.repositories.db_models import users
from std_cards.models.auth import UserDB, UserRole

logger = logging.getLogger(__name__)


async def seed_super_admin() -> None:
    """Idempotent: создаёт super-admin из ENV если не существует."""
    sm = get_session_maker()
    repo = UserRepository(sm)
    existing = await repo.get_by_email(settings.SEED.SUPER_ADMIN_EMAIL)
    if existing is not None:
        logger.info("Super-admin already exists: %s", settings.SEED.SUPER_ADMIN_EMAIL)
        return
    password_hash = hash_password(settings.SEED.SUPER_ADMIN_PASSWORD)
    async with sm.session() as conn:
        result = await conn.execute(
            sa.insert(users)
            .values(
                email=settings.SEED.SUPER_ADMIN_EMAIL,
                password_hash=password_hash,
                role=UserRole.SUPER_ADMIN,
            )
            .returning(users)
        )
        row = result.fetchone()
    user = UserDB.model_validate(row, from_attributes=True)
    logger.info("Created super-admin: %s (id=%s)", user.email, user.id)


def main() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL)
    asyncio.run(seed_super_admin())


if __name__ == "__main__":
    main()
