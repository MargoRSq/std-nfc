import pyotp
import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.infrastructure.repositories.db_models import password_resets
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole


@pytest.fixture
def user_repo(session_maker):
    return UserRepository(session_maker)


async def test_login_no_2fa_returns_tokens(client: AsyncClient, user_repo):
    pw = "Strong#Pass1"
    await user_repo.create(
        UserCreate(email="api1@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    r = await client.post("/api/auth/login", json={"email": "api1@x.com", "password": pw})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "api1@x.com"


async def test_login_with_2fa_returns_challenge(client: AsyncClient, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="api2@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=[])
    r = await client.post("/api/auth/login", json={"email": "api2@x.com", "password": pw})
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "totp_required"
    assert body["challenge_token"]


async def test_login_totp_completes_2fa(client: AsyncClient, user_repo):
    pw = "p"
    user = await user_repo.create(
        UserCreate(email="api3@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    secret = pyotp.random_base32()
    await user_repo.set_totp(user.id, secret=secret, enabled=True, recovery_codes=[])
    r1 = (await client.post("/api/auth/login", json={"email": "api3@x.com", "password": pw})).json()
    code = pyotp.TOTP(secret).now()
    r2 = await client.post(
        "/api/auth/login/totp", json={"challenge_token": r1["challenge_token"], "code": code}
    )
    assert r2.status_code == 200
    assert r2.json()["access_token"]


async def test_login_wrong_password_401(client: AsyncClient, user_repo):
    await user_repo.create(
        UserCreate(email="api4@x.com", password_hash=hash_password("right"), role=UserRole.ADMIN)
    )
    r = await client.post("/api/auth/login", json={"email": "api4@x.com", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"


async def test_login_validation_error(client: AsyncClient):
    r = await client.post("/api/auth/login", json={"email": "not-email", "password": ""})
    assert r.status_code == 422


async def test_refresh_rotation(client: AsyncClient, user_repo):
    await user_repo.create(
        UserCreate(email="api5@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    login = (
        await client.post("/api/auth/login", json={"email": "api5@x.com", "password": "p"})
    ).json()
    r = await client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != login["refresh_token"]


async def test_refresh_reuse_detection_401(client: AsyncClient, user_repo):
    await user_repo.create(
        UserCreate(email="api6@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    login = (
        await client.post("/api/auth/login", json={"email": "api6@x.com", "password": "p"})
    ).json()
    await client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    r = await client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 401
    assert r.json()["code"] == "refresh_reuse_detected"


async def test_logout_revokes(client: AsyncClient, user_repo):
    await user_repo.create(
        UserCreate(email="api7@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    login = (
        await client.post("/api/auth/login", json={"email": "api7@x.com", "password": "p"})
    ).json()
    r = await client.post("/api/auth/logout", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 204
    r2 = await client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r2.status_code == 401


async def test_me_requires_auth(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_me_returns_user(client: AsyncClient, user_repo):
    await user_repo.create(
        UserCreate(email="api8@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    login = (
        await client.post("/api/auth/login", json={"email": "api8@x.com", "password": "p"})
    ).json()
    r = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == "api8@x.com"


async def test_totp_enroll_then_verify(client: AsyncClient, user_repo):
    await user_repo.create(
        UserCreate(email="api9@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    login = (
        await client.post("/api/auth/login", json={"email": "api9@x.com", "password": "p"})
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    enroll = await client.post("/api/auth/totp/enroll", headers=headers)
    assert enroll.status_code == 200
    body = enroll.json()
    assert body["otpauth_url"].startswith("otpauth://")
    user = await user_repo.get_by_email("api9@x.com")
    code = pyotp.TOTP(user.totp_secret).now()
    verify = await client.post("/api/auth/totp/verify", json={"code": code}, headers=headers)
    assert verify.status_code == 200
    assert len(verify.json()["recovery_codes"]) == 10


async def test_password_reset_creates_row(client: AsyncClient, user_repo, session_maker):
    """End-to-end: reset request → 204 + row в БД."""
    user = await user_repo.create(
        UserCreate(email="api10@x.com", password_hash=hash_password("old"), role=UserRole.ADMIN)
    )
    r = await client.post("/api/auth/password/reset/request", json={"email": "api10@x.com"})
    assert r.status_code == 204
    async with session_maker.session() as conn:
        result = await conn.execute(
            sa.select(password_resets).where(password_resets.c.user_id == user.id)
        )
        rows = result.fetchall()
        assert len(rows) >= 1


async def test_password_reset_unknown_email_still_204(client: AsyncClient):
    r = await client.post("/api/auth/password/reset/request", json={"email": "ghost@x.com"})
    assert r.status_code == 204
