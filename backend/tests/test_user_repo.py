from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole


async def test_create_and_get_by_email(session_maker):
    repo = UserRepository(session_maker)
    user = await repo.create(
        UserCreate(email="t1@example.com", password_hash="h1", role=UserRole.ADMIN)
    )
    assert user.email == "t1@example.com"
    fetched = await repo.get_by_email("t1@example.com")
    assert fetched is not None
    assert fetched.id == user.id


async def test_get_by_email_citext_case_insensitive(session_maker):
    repo = UserRepository(session_maker)
    await repo.create(UserCreate(email="Mixed@Case.com", password_hash="h", role=UserRole.ADMIN))
    fetched = await repo.get_by_email("mixed@case.com")
    assert fetched is not None


async def test_get_by_id_not_found(session_maker):
    repo = UserRepository(session_maker)
    assert await repo.get_by_id(uuid4()) is None


async def test_increment_failed_login_locks_after_max(session_maker):
    repo = UserRepository(session_maker)
    user = await repo.create(UserCreate(email="lock@x.com", password_hash="h", role=UserRole.ADMIN))
    for _ in range(5):
        await repo.increment_failed_login(user.id, max_attempts=5, lockout_minutes=15)
    assert await repo.is_locked(user.id) is True


async def test_reset_failed_login_clears_lockout(session_maker):
    repo = UserRepository(session_maker)
    user = await repo.create(
        UserCreate(email="reset@x.com", password_hash="h", role=UserRole.ADMIN)
    )
    for _ in range(5):
        await repo.increment_failed_login(user.id, max_attempts=5)
    await repo.reset_failed_login(user.id)
    fresh = await repo.get_by_id(user.id)
    assert fresh.failed_login_attempts == 0
    assert fresh.locked_until is None


async def test_bump_token_version(session_maker):
    repo = UserRepository(session_maker)
    user = await repo.create(UserCreate(email="bump@x.com", password_hash="h", role=UserRole.ADMIN))
    new_version = await repo.bump_token_version(user.id)
    assert new_version == 1
    new_version = await repo.bump_token_version(user.id)
    assert new_version == 2


async def test_set_totp_and_consume_recovery(session_maker):
    repo = UserRepository(session_maker)
    user = await repo.create(UserCreate(email="totp@x.com", password_hash="h", role=UserRole.ADMIN))
    await repo.set_totp(user.id, secret="ABC123", enabled=True, recovery_codes=["c1", "c2", "c3"])
    fresh = await repo.get_by_id(user.id)
    assert fresh.totp_enabled is True
    assert fresh.totp_secret == "ABC123"
    assert sorted(fresh.recovery_codes) == ["c1", "c2", "c3"]
    consumed = await repo.consume_recovery_code(user.id, "c1")
    assert consumed is True
    fresh = await repo.get_by_id(user.id)
    assert sorted(fresh.recovery_codes) == ["c2", "c3"]
    consumed_again = await repo.consume_recovery_code(user.id, "c1")
    assert consumed_again is False


async def test_consume_recovery_code_atomic_concurrent(session_maker):
    """Two concurrent consumes одного кода — только один True."""
    import asyncio

    repo = UserRepository(session_maker)
    user = await repo.create(UserCreate(email="race@x.com", password_hash="h", role=UserRole.ADMIN))
    await repo.set_totp(user.id, secret="X", enabled=True, recovery_codes=["onlyone"])
    results = await asyncio.gather(
        repo.consume_recovery_code(user.id, "onlyone"),
        repo.consume_recovery_code(user.id, "onlyone"),
    )
    assert sorted(results) == [False, True]


async def test_unique_email_constraint_raises(session_maker):
    repo = UserRepository(session_maker)
    await repo.create(UserCreate(email="dup@x.com", password_hash="h", role=UserRole.ADMIN))
    with pytest.raises(IntegrityError):
        await repo.create(UserCreate(email="dup@x.com", password_hash="h2", role=UserRole.ADMIN))
