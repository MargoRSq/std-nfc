import pyotp
import pytest
import sqlalchemy as sa

from std_cards.core.exceptions import (
    ConflictError,
    ForbiddenError,
    UnauthorizedError,
)
from std_cards.core.ratelimit import SlidingWindowRateLimiter, login_rate_limiter
from std_cards.core.security import hash_password
from std_cards.infrastructure.repositories import (
    LoginChallengeRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
    UserRepository,
)
from std_cards.infrastructure.repositories.db_models import users
from std_cards.models.auth import UserCreate, UserRole
from std_cards.services.auth_service import AuthService


@pytest.fixture
def auth_service(session_maker):
    return AuthService(
        user_repo=UserRepository(session_maker),
        refresh_repo=RefreshTokenRepository(session_maker),
        challenge_repo=LoginChallengeRepository(session_maker),
        password_reset_repo=PasswordResetRepository(session_maker),
    )


@pytest.fixture
def user_repo(session_maker):
    return UserRepository(session_maker)


@pytest.fixture(autouse=True)
async def _clear_rate_limiter():
    await login_rate_limiter.cleanup_expired()
    async with login_rate_limiter._lock:
        login_rate_limiter._buckets.clear()


# === Login ===


async def test_login_no_2fa_returns_tokens(auth_service, user_repo):
    pw = "Strong#Pass1"
    await user_repo.create(
        UserCreate(email="a@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    res = await auth_service.login_step1("a@x.com", pw)
    assert res["stage"] == "completed"
    assert res["access_token"]
    assert res["refresh_token"]
    assert res["user"]["email"] == "a@x.com"


async def test_login_with_2fa_returns_challenge(auth_service, user_repo):
    pw = "Strong#Pass1"
    user = await user_repo.create(
        UserCreate(email="b@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=[])
    res = await auth_service.login_step1("b@x.com", pw)
    assert res["stage"] == "totp_required"
    assert res["challenge_token"]


async def test_login_wrong_password_raises(auth_service, user_repo):
    await user_repo.create(
        UserCreate(email="c@x.com", password_hash=hash_password("right"), role=UserRole.ADMIN)
    )
    with pytest.raises(UnauthorizedError) as exc_info:
        await auth_service.login_step1("c@x.com", "wrong")
    assert exc_info.value.CODE == "invalid_credentials"


async def test_login_unknown_email_raises_unauthorized(auth_service):
    with pytest.raises(UnauthorizedError):
        await auth_service.login_step1("nope@x.com", "any")


async def test_login_inactive_user_raises_forbidden(auth_service, user_repo, session_maker):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="off@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    async with session_maker.session() as conn:
        await conn.execute(sa.update(users).where(users.c.id == user.id).values(is_active=False))
    with pytest.raises(ForbiddenError):
        await auth_service.login_step1("off@x.com", pw)


async def test_login_locked_user_raises(auth_service, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="lock@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    for _ in range(5):
        await user_repo.increment_failed_login(user.id, max_attempts=5, lockout_minutes=15)
    with pytest.raises(UnauthorizedError):
        await auth_service.login_step1("lock@x.com", pw)


async def test_login_rate_limit(auth_service, user_repo):
    """Использует отдельный limiter с лимитом=3 вместо monkeypatch frozen settings."""
    limited_limiter = SlidingWindowRateLimiter()
    await user_repo.create(
        UserCreate(email="rl@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )

    for _ in range(3):
        ok = await limited_limiter.check(
            scope="login", identifier="rl@x.com", limit=3, window_seconds=60
        )
        assert ok

    ok = await limited_limiter.check(
        scope="login", identifier="rl@x.com", limit=3, window_seconds=60
    )
    assert not ok


# === Login step 2 TOTP ===


async def test_login_step2_totp_completes(auth_service, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="t1@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=[])
    res1 = await auth_service.login_step1("t1@x.com", pw)
    code = pyotp.TOTP(secret).now()
    res2 = await auth_service.login_step2_totp(res1["challenge_token"], code)
    assert res2["stage"] == "completed"
    assert res2["access_token"]


async def test_login_step2_totp_wrong_code(auth_service, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="t2@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=[])
    res1 = await auth_service.login_step1("t2@x.com", pw)
    with pytest.raises(UnauthorizedError):
        await auth_service.login_step2_totp(res1["challenge_token"], "000000")


async def test_login_step2_challenge_replay_rejected(auth_service, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="t3@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=[])
    res1 = await auth_service.login_step1("t3@x.com", pw)
    code = pyotp.TOTP(secret).now()
    await auth_service.login_step2_totp(res1["challenge_token"], code)
    with pytest.raises(UnauthorizedError):
        await auth_service.login_step2_totp(res1["challenge_token"], code)


# === Recovery codes ===


async def test_login_recovery_code_consumes_one(auth_service, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="r1@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    plain_codes = ["RECOVERY12AB", "RECOVERY12CD"]
    bcrypt_hashes = [hash_password(c) for c in plain_codes]
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=bcrypt_hashes)
    res1 = await auth_service.login_step1("r1@x.com", pw)
    res2 = await auth_service.login_step2_recovery(res1["challenge_token"], "RECOVERY12AB")
    assert res2["stage"] == "completed"
    fresh = await user_repo.get_by_id(user.id)
    assert len(fresh.recovery_codes) == 1


# === Refresh rotation ===


async def test_refresh_rotation_returns_new_pair(auth_service, user_repo):
    pw = "p"
    await user_repo.create(
        UserCreate(email="rf@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    res1 = await auth_service.login_step1("rf@x.com", pw)
    res2 = await auth_service.refresh_tokens(res1["refresh_token"])
    assert res2["refresh_token"] != res1["refresh_token"]
    assert res2["access_token"]


async def test_refresh_reuse_detection_revokes_chain(auth_service, user_repo):
    pw = "p"
    await user_repo.create(
        UserCreate(email="reuse@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    res1 = await auth_service.login_step1("reuse@x.com", pw)
    res2 = await auth_service.refresh_tokens(res1["refresh_token"])
    with pytest.raises(UnauthorizedError) as exc:
        await auth_service.refresh_tokens(res1["refresh_token"])
    assert "suspicious" in exc.value.message.lower() or exc.value.CODE == "unauthorized"
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh_tokens(res2["refresh_token"])


async def test_refresh_invalid_token(auth_service):
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh_tokens("nope")


# === Logout / force_logout_all ===


async def test_logout_revokes_refresh(auth_service, user_repo):
    pw = "p"
    await user_repo.create(
        UserCreate(email="lo@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    res = await auth_service.login_step1("lo@x.com", pw)
    await auth_service.logout(res["refresh_token"])
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh_tokens(res["refresh_token"])


async def test_force_logout_all_invalidates_access_token(auth_service, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="fl@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    res = await auth_service.login_step1("fl@x.com", pw)
    access = res["access_token"]
    await auth_service.force_logout_all(user.id)
    with pytest.raises(UnauthorizedError):
        await auth_service.get_current_user(access)


# === TOTP enroll ===


async def test_totp_enroll_returns_qr(auth_service, user_repo):
    user = await user_repo.create(
        UserCreate(email="en@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    res = await auth_service.totp_enroll(user.id)
    assert res["otpauth_url"].startswith("otpauth://")
    assert res["qr_png_base64"]
    fresh = await user_repo.get_by_id(user.id)
    assert fresh.totp_secret is not None
    assert fresh.totp_enabled is False


async def test_totp_verify_enables_and_returns_recovery(auth_service, user_repo):
    user = await user_repo.create(
        UserCreate(email="ev@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await auth_service.totp_enroll(user.id)
    fresh = await user_repo.get_by_id(user.id)
    code = pyotp.TOTP(fresh.totp_secret).now()
    verify_res = await auth_service.totp_verify(user.id, code)
    assert len(verify_res["recovery_codes"]) == 10
    fresh = await user_repo.get_by_id(user.id)
    assert fresh.totp_enabled is True


async def test_totp_already_enabled_raises(auth_service, user_repo):
    user = await user_repo.create(
        UserCreate(email="al@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await user_repo.set_totp(user.id, secret=pyotp.random_base32(), enabled=True, recovery_codes=[])
    with pytest.raises(ConflictError):
        await auth_service.totp_enroll(user.id)


async def test_totp_disable(auth_service, user_repo):
    user = await user_repo.create(
        UserCreate(email="dis@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=[])
    code = pyotp.TOTP(secret).now()
    await auth_service.totp_disable(user.id, "p", code)
    fresh = await user_repo.get_by_id(user.id)
    assert fresh.totp_enabled is False
    assert fresh.totp_secret is None


# === Password reset ===


async def test_password_reset_request_returns_token(auth_service, user_repo):
    await user_repo.create(
        UserCreate(email="pr@x.com", password_hash=hash_password("old"), role=UserRole.ADMIN)
    )
    token = await auth_service.password_reset_request("pr@x.com")
    assert token


async def test_password_reset_request_unknown_email_returns_none(auth_service):
    token = await auth_service.password_reset_request("nope@x.com")
    assert token is None


async def test_password_reset_confirm_changes_password(auth_service, user_repo):
    await user_repo.create(
        UserCreate(email="pc@x.com", password_hash=hash_password("old"), role=UserRole.ADMIN)
    )
    token = await auth_service.password_reset_request("pc@x.com")
    await auth_service.password_reset_confirm(token, "new_password")
    res = await auth_service.login_step1("pc@x.com", "new_password")
    assert res["stage"] == "completed"
    with pytest.raises(UnauthorizedError):
        await auth_service.login_step1("pc@x.com", "old")


async def test_password_reset_token_replay_rejected(auth_service, user_repo):
    await user_repo.create(
        UserCreate(email="pr2@x.com", password_hash=hash_password("old"), role=UserRole.ADMIN)
    )
    token = await auth_service.password_reset_request("pr2@x.com")
    await auth_service.password_reset_confirm(token, "new1")
    with pytest.raises(UnauthorizedError):
        await auth_service.password_reset_confirm(token, "new2")


# === get_current_user ===


async def test_get_current_user_valid(auth_service, user_repo):
    user = await user_repo.create(
        UserCreate(email="me@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    res = await auth_service.login_step1("me@x.com", "p")
    me = await auth_service.get_current_user(res["access_token"])
    assert me.id == user.id


async def test_get_current_user_token_version_mismatch(auth_service, user_repo):
    user = await user_repo.create(
        UserCreate(email="tv@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    res = await auth_service.login_step1("tv@x.com", "p")
    await user_repo.bump_token_version(user.id)
    with pytest.raises(UnauthorizedError):
        await auth_service.get_current_user(res["access_token"])
