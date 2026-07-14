from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import users
from std_cards.models.auth import UserCreate, UserDB


class UserRepository(BaseRepository):
    async def get_by_id(self, user_id: UUID, conn: AsyncConnection | None = None) -> UserDB | None:
        result = await self.ctx_wrap(sa.select(users).where(users.c.id == user_id), conn)
        row = result.fetchone()
        return UserDB.model_validate(row, from_attributes=True) if row else None

    async def get_by_email(self, email: str, conn: AsyncConnection | None = None) -> UserDB | None:
        result = await self.ctx_wrap(sa.select(users).where(users.c.email == email), conn)
        row = result.fetchone()
        return UserDB.model_validate(row, from_attributes=True) if row else None

    async def create(self, data: UserCreate, conn: AsyncConnection | None = None) -> UserDB:
        result = await self.ctx_wrap(
            sa.insert(users).values(**data.model_dump(mode="python")).returning(users),
            conn,
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create user")
        return UserDB.model_validate(row, from_attributes=True)

    async def update_password(
        self, user_id: UUID, password_hash: str, conn: AsyncConnection | None = None
    ) -> None:
        await self.ctx_wrap(
            sa.update(users).where(users.c.id == user_id).values(password_hash=password_hash),
            conn,
        )

    async def set_totp(
        self,
        user_id: UUID,
        secret: str | None,
        enabled: bool,
        recovery_codes: list[str] | None,
        conn: AsyncConnection | None = None,
    ) -> None:
        await self.ctx_wrap(
            sa.update(users)
            .where(users.c.id == user_id)
            .values(
                totp_secret=secret,
                totp_enabled=enabled,
                recovery_codes=recovery_codes,
                last_totp_step=None,
            ),
            conn,
        )

    async def set_last_totp_step(
        self, user_id: UUID, step: int, conn: AsyncConnection | None = None
    ) -> None:
        """Persist the period index of the last accepted TOTP code (replay guard)."""
        await self.ctx_wrap(
            sa.update(users).where(users.c.id == user_id).values(last_totp_step=step),
            conn,
        )

    async def advance_totp_step(
        self, user_id: UUID, step: int, conn: AsyncConnection | None = None
    ) -> bool:
        """Атомарно двигает last_totp_step вперёд только если step новее сохранённого.

        Conditional UPDATE служит CAS-гейтом против replay под конкурентностью:
        два параллельных логина с одним и тем же кодом читают один stale snapshot и
        оба проходят verify, но эту запись выиграет лишь один — второй получит 0 строк
        (replay) и должен быть отклонён. Возвращает True, если step применён.
        """
        result = await self.ctx_wrap(
            sa.update(users)
            .where(
                (users.c.id == user_id)
                & ((users.c.last_totp_step.is_(None)) | (users.c.last_totp_step < step))
            )
            .values(last_totp_step=step)
            .returning(users.c.id),
            conn,
        )
        return result.fetchone() is not None

    async def consume_recovery_code(
        self, user_id: UUID, code_hash: str, conn: AsyncConnection | None = None
    ) -> bool:
        """Атомарно потребляет recovery_code (one-shot). Возвращает True если код найден и удалён."""
        result = await self.ctx_wrap(
            sa.update(users)
            .where(
                (users.c.id == user_id)
                & (sa.literal(code_hash) == sa.func.any_(users.c.recovery_codes))
            )
            .values(recovery_codes=sa.func.array_remove(users.c.recovery_codes, code_hash))
            .returning(users.c.id),
            conn,
        )
        return result.fetchone() is not None

    async def increment_failed_login(
        self,
        user_id: UUID,
        max_attempts: int = 5,
        lockout_minutes: int = 15,
        conn: AsyncConnection | None = None,
    ) -> None:
        """Атомарно: +1 счётчик, при достижении max_attempts — locked_until = now+lockout_minutes.

        Если предыдущий lockout истёк, счётчик сбрасывается на 1 (свежий fail-цикл).
        """
        lockout_interval_seconds = lockout_minutes * 60
        query = sa.text("""
            UPDATE users SET
                failed_login_attempts = CASE
                    WHEN locked_until IS NOT NULL AND locked_until < NOW() THEN 1
                    ELSE failed_login_attempts + 1
                END,
                locked_until = CASE
                    WHEN locked_until IS NOT NULL AND locked_until < NOW() THEN NULL
                    WHEN failed_login_attempts + 1 >= :max_attempts THEN NOW() + (:lockout_seconds || ' seconds')::interval
                    ELSE locked_until
                END
            WHERE id = :user_id
        """).bindparams(
            user_id=user_id, max_attempts=max_attempts, lockout_seconds=lockout_interval_seconds
        )
        await self.ctx_wrap(query, conn)

    async def reset_failed_login(self, user_id: UUID, conn: AsyncConnection | None = None) -> None:
        await self.ctx_wrap(
            sa.update(users)
            .where(users.c.id == user_id)
            .values(
                failed_login_attempts=0,
                locked_until=None,
                last_login_at=datetime.now(UTC),
            ),
            conn,
        )

    async def list_by_roles(
        self, roles: list[str], conn: AsyncConnection | None = None
    ) -> list[UserDB]:
        result = await self.ctx_wrap(
            sa.select(users).where(users.c.role.in_(roles)).order_by(users.c.created_at.asc()),
            conn,
        )
        return [UserDB.model_validate(row, from_attributes=True) for row in result.fetchall()]

    async def set_active(
        self, user_id: UUID, is_active: bool, conn: AsyncConnection | None = None
    ) -> None:
        await self.ctx_wrap(
            sa.update(users).where(users.c.id == user_id).values(is_active=is_active),
            conn,
        )

    async def update_fields(
        self, user_id: UUID, fields: dict, conn: AsyncConnection | None = None
    ) -> UserDB | None:
        fields["updated_at"] = sa.func.now()
        result = await self.ctx_wrap(
            sa.update(users).where(users.c.id == user_id).values(**fields).returning(users),
            conn,
        )
        row = result.fetchone()
        return UserDB.model_validate(row, from_attributes=True) if row else None

    async def bump_token_version(self, user_id: UUID, conn: AsyncConnection | None = None) -> int:
        result = await self.ctx_wrap(
            sa.update(users)
            .where(users.c.id == user_id)
            .values(token_version=users.c.token_version + 1)
            .returning(users.c.token_version),
            conn,
        )
        row = result.fetchone()
        if row is None:
            raise ValueError(f"User {user_id} not found")
        return row.token_version

    async def is_locked(self, user_id: UUID, conn: AsyncConnection | None = None) -> bool:
        result = await self.ctx_wrap(
            sa.select(users.c.locked_until).where(users.c.id == user_id), conn
        )
        row = result.fetchone()
        if not row or not row.locked_until:
            return False
        return row.locked_until > datetime.now(UTC)
