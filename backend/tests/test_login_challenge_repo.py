from datetime import UTC, datetime, timedelta

from std_cards.infrastructure.repositories.login_challenge_repo import LoginChallengeRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import ConsumeResult, UserCreate, UserRole


async def _make_user(session_maker, email="challenge_user@x.com"):
    repo = UserRepository(session_maker)
    return await repo.create(UserCreate(email=email, password_hash="h", role=UserRole.ADMIN))


async def test_create_and_get_by_hash(session_maker):
    user = await _make_user(session_maker)
    repo = LoginChallengeRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(minutes=10)
    challenge = await repo.create(user.id, challenge_hash="chash1", expires_at=expires)
    assert challenge.user_id == user.id
    fetched = await repo.get_by_hash("chash1")
    assert fetched is not None
    assert fetched.id == challenge.id


async def test_get_by_hash_not_found(session_maker):
    repo = LoginChallengeRepository(session_maker)
    assert await repo.get_by_hash("nonexistent") is None


async def test_consume_once_returns_consumed(session_maker):
    user = await _make_user(session_maker)
    repo = LoginChallengeRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(minutes=10)
    challenge = await repo.create(user.id, challenge_hash="chash2", expires_at=expires)
    result = await repo.consume(challenge.id)
    assert result == ConsumeResult.CONSUMED
    fetched = await repo.get_by_hash("chash2")
    assert fetched.consumed_at is not None


async def test_consume_twice_returns_already_consumed(session_maker):
    user = await _make_user(session_maker)
    repo = LoginChallengeRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(minutes=10)
    challenge = await repo.create(user.id, challenge_hash="chash3", expires_at=expires)
    assert await repo.consume(challenge.id) == ConsumeResult.CONSUMED
    assert await repo.consume(challenge.id) == ConsumeResult.ALREADY_CONSUMED


async def test_consume_expired_returns_expired(session_maker):
    user = await _make_user(session_maker)
    repo = LoginChallengeRepository(session_maker)
    past = datetime.now(UTC) - timedelta(seconds=1)
    challenge = await repo.create(user.id, challenge_hash="chash4", expires_at=past)
    result = await repo.consume(challenge.id)
    assert result == ConsumeResult.EXPIRED


async def test_consume_not_found_returns_not_found(session_maker):
    from uuid import uuid4

    repo = LoginChallengeRepository(session_maker)
    result = await repo.consume(uuid4())
    assert result == ConsumeResult.NOT_FOUND


async def test_cleanup_expired(session_maker):
    user = await _make_user(session_maker)
    repo = LoginChallengeRepository(session_maker)

    future = datetime.now(UTC) + timedelta(minutes=10)
    past = datetime.now(UTC) - timedelta(seconds=1)

    await repo.create(user.id, challenge_hash="cexp1", expires_at=past)
    await repo.create(user.id, challenge_hash="cexp2", expires_at=past)
    await repo.create(user.id, challenge_hash="ckeep1", expires_at=future)

    count = await repo.cleanup_expired()
    assert count == 2
    assert await repo.get_by_hash("ckeep1") is not None
