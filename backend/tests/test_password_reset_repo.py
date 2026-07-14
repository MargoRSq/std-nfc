from datetime import UTC, datetime, timedelta

from std_cards.infrastructure.repositories.password_reset_repo import PasswordResetRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import ConsumeResult, UserCreate, UserRole


async def _make_user(session_maker, email="reset_user@x.com"):
    repo = UserRepository(session_maker)
    return await repo.create(UserCreate(email=email, password_hash="h", role=UserRole.ADMIN))


async def test_create_and_get_by_hash(session_maker):
    user = await _make_user(session_maker)
    repo = PasswordResetRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(hours=1)
    reset = await repo.create(user.id, token_hash="rhash1", expires_at=expires)
    assert reset.user_id == user.id
    fetched = await repo.get_by_hash("rhash1")
    assert fetched is not None
    assert fetched.id == reset.id


async def test_get_by_hash_not_found(session_maker):
    repo = PasswordResetRepository(session_maker)
    assert await repo.get_by_hash("nonexistent") is None


async def test_consume_once_returns_consumed(session_maker):
    user = await _make_user(session_maker)
    repo = PasswordResetRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(hours=1)
    reset = await repo.create(user.id, token_hash="rhash2", expires_at=expires)
    result = await repo.consume(reset.id)
    assert result == ConsumeResult.CONSUMED
    fetched = await repo.get_by_hash("rhash2")
    assert fetched.consumed_at is not None


async def test_consume_twice_returns_already_consumed(session_maker):
    user = await _make_user(session_maker)
    repo = PasswordResetRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(hours=1)
    reset = await repo.create(user.id, token_hash="rhash3", expires_at=expires)
    assert await repo.consume(reset.id) == ConsumeResult.CONSUMED
    assert await repo.consume(reset.id) == ConsumeResult.ALREADY_CONSUMED


async def test_consume_expired_returns_expired(session_maker):
    user = await _make_user(session_maker)
    repo = PasswordResetRepository(session_maker)
    past = datetime.now(UTC) - timedelta(seconds=1)
    reset = await repo.create(user.id, token_hash="rhash4", expires_at=past)
    result = await repo.consume(reset.id)
    assert result == ConsumeResult.EXPIRED


async def test_consume_not_found_returns_not_found(session_maker):
    from uuid import uuid4

    repo = PasswordResetRepository(session_maker)
    result = await repo.consume(uuid4())
    assert result == ConsumeResult.NOT_FOUND


async def test_cleanup_expired(session_maker):
    user = await _make_user(session_maker)
    repo = PasswordResetRepository(session_maker)

    future = datetime.now(UTC) + timedelta(hours=1)
    past = datetime.now(UTC) - timedelta(seconds=1)

    await repo.create(user.id, token_hash="rexp1", expires_at=past)
    await repo.create(user.id, token_hash="rexp2", expires_at=past)
    await repo.create(user.id, token_hash="rkeep1", expires_at=future)

    count = await repo.cleanup_expired()
    assert count == 2
    assert await repo.get_by_hash("rkeep1") is not None
