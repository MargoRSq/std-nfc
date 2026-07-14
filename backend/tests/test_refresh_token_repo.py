from datetime import UTC, datetime, timedelta

from std_cards.infrastructure.repositories.refresh_token_repo import RefreshTokenRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole


async def _make_user(session_maker, email="user@x.com"):
    repo = UserRepository(session_maker)
    return await repo.create(UserCreate(email=email, password_hash="h", role=UserRole.ADMIN))


async def test_create_and_get_by_hash(session_maker):
    user = await _make_user(session_maker)
    repo = RefreshTokenRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(days=30)
    token = await repo.create(user.id, token_hash="hash1", expires_at=expires)
    assert token.user_id == user.id
    fetched = await repo.get_by_hash("hash1")
    assert fetched is not None
    assert fetched.id == token.id


async def test_get_by_hash_not_found(session_maker):
    repo = RefreshTokenRepository(session_maker)
    assert await repo.get_by_hash("nonexistent") is None


async def test_revoke(session_maker):
    user = await _make_user(session_maker)
    repo = RefreshTokenRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(days=30)
    token = await repo.create(user.id, token_hash="hash2", expires_at=expires)
    await repo.revoke(token.id)
    fetched = await repo.get_by_hash("hash2")
    assert fetched.revoked_at is not None


async def test_revoke_with_replaced_by(session_maker):
    user = await _make_user(session_maker)
    repo = RefreshTokenRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(days=30)
    old_token = await repo.create(user.id, token_hash="old_hash", expires_at=expires)
    new_token = await repo.create(user.id, token_hash="new_hash", expires_at=expires)
    await repo.revoke(old_token.id, replaced_by_id=new_token.id)
    fetched = await repo.get_by_hash("old_hash")
    assert fetched.revoked_at is not None
    assert fetched.replaced_by_id == new_token.id


async def test_revoke_chain_from_revokes_whole_family(session_maker):
    user_repo = UserRepository(session_maker)
    refresh_repo = RefreshTokenRepository(session_maker)
    user = await user_repo.create(
        UserCreate(email="chain@x.com", password_hash="h", role=UserRole.ADMIN)
    )

    t1 = await refresh_repo.create(user.id, "h1", datetime.now(UTC) + timedelta(days=7))
    t2 = await refresh_repo.create(
        user.id, "h2", datetime.now(UTC) + timedelta(days=7), family_id=t1.family_id
    )
    await refresh_repo.revoke(t1.id, replaced_by_id=t2.id)
    t3 = await refresh_repo.create(
        user.id, "h3", datetime.now(UTC) + timedelta(days=7), family_id=t1.family_id
    )
    await refresh_repo.revoke(t2.id, replaced_by_id=t3.id)

    count = await refresh_repo.revoke_chain_from(t1.id)
    assert count == 1
    fresh_t3 = await refresh_repo.get_by_hash("h3")
    assert fresh_t3.revoked_at is not None


async def test_revoke_chain_from_does_not_affect_other_user(session_maker):
    user_repo = UserRepository(session_maker)
    refresh_repo = RefreshTokenRepository(session_maker)
    u1 = await user_repo.create(UserCreate(email="a@x.com", password_hash="h", role=UserRole.ADMIN))
    u2 = await user_repo.create(UserCreate(email="b@x.com", password_hash="h", role=UserRole.ADMIN))
    t1 = await refresh_repo.create(u1.id, "h_a", datetime.now(UTC) + timedelta(days=7))
    await refresh_repo.create(u2.id, "h_b", datetime.now(UTC) + timedelta(days=7))
    await refresh_repo.revoke_chain_from(t1.id)
    fresh_t2 = await refresh_repo.get_by_hash("h_b")
    assert fresh_t2.revoked_at is None


async def test_revoke_all_for_user(session_maker):
    user = await _make_user(session_maker)
    repo = RefreshTokenRepository(session_maker)
    expires = datetime.now(UTC) + timedelta(days=30)
    await repo.create(user.id, token_hash="u1", expires_at=expires)
    await repo.create(user.id, token_hash="u2", expires_at=expires)
    await repo.create(user.id, token_hash="u3", expires_at=expires)
    count = await repo.revoke_all_for_user(user.id)
    assert count == 3


async def test_get_active_for_user_excludes_revoked_and_expired(session_maker):
    user = await _make_user(session_maker)
    repo = RefreshTokenRepository(session_maker)

    future = datetime.now(UTC) + timedelta(days=30)
    past = datetime.now(UTC) - timedelta(seconds=1)

    active = await repo.create(user.id, token_hash="active1", expires_at=future)
    expired = await repo.create(user.id, token_hash="expired1", expires_at=past)
    revoked = await repo.create(user.id, token_hash="revoked1", expires_at=future)
    await repo.revoke(revoked.id)

    active_list = await repo.get_active_for_user(user.id)
    active_ids = {t.id for t in active_list}
    assert active.id in active_ids
    assert expired.id not in active_ids
    assert revoked.id not in active_ids


async def test_cleanup_expired(session_maker):
    user = await _make_user(session_maker)
    repo = RefreshTokenRepository(session_maker)

    future = datetime.now(UTC) + timedelta(days=30)
    past = datetime.now(UTC) - timedelta(seconds=1)

    await repo.create(user.id, token_hash="exp1", expires_at=past)
    await repo.create(user.id, token_hash="exp2", expires_at=past)
    await repo.create(user.id, token_hash="keep1", expires_at=future)

    count = await repo.cleanup_expired()
    assert count == 2
    assert await repo.get_by_hash("keep1") is not None


async def test_create_with_ip_round_trip(session_maker):
    user = await _make_user(session_maker, email="ipt@x.com")
    repo = RefreshTokenRepository(session_maker)
    t = await repo.create(user.id, "ip_h", datetime.now(UTC) + timedelta(days=1), ip="192.0.2.5")
    assert isinstance(t.ip, str)
    assert t.ip == "192.0.2.5"
    fresh = await repo.get_by_hash("ip_h")
    assert fresh.ip == "192.0.2.5"
