from uuid import uuid4

from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole


async def _create_user(session_maker, role: UserRole):
    repo = UserRepository(session_maker)
    return await repo.create(
        UserCreate(
            email=f"u{uuid4().hex[:8]}@x.com",
            password_hash=hash_password("pass"),
            role=role,
        )
    )


async def _login(client: AsyncClient, email: str, password: str = "pass") -> str:
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


async def test_list_admins_super_admin_only(client: AsyncClient, session_maker):
    super_admin = await _create_user(session_maker, UserRole.SUPER_ADMIN)
    admin = await _create_user(session_maker, UserRole.ADMIN)

    token = await _login(client, super_admin.email)
    r = await client.get("/api/admins/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    admin_token = await _login(client, admin.email)
    r2 = await client.get("/api/admins/", headers={"Authorization": f"Bearer {admin_token}"})
    assert r2.status_code == 403


async def test_create_admin_returns_temp_password(client: AsyncClient, session_maker):
    super_admin = await _create_user(session_maker, UserRole.SUPER_ADMIN)
    token = await _login(client, super_admin.email)

    r = await client.post(
        "/api/admins/",
        json={"email": f"new{uuid4().hex[:6]}@x.com", "category_ids": [1]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert "temporary_password" in body
    assert len(body["temporary_password"]) >= 12
    assert body["user"]["role"] == "admin"


async def test_create_admin_duplicate_email_409(client: AsyncClient, session_maker):
    super_admin = await _create_user(session_maker, UserRole.SUPER_ADMIN)
    token = await _login(client, super_admin.email)
    email = f"dup{uuid4().hex[:6]}@x.com"

    await client.post(
        "/api/admins/",
        json={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    r2 = await client.post(
        "/api/admins/",
        json={"email": email},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409


async def test_reset_password_returns_new_password(client: AsyncClient, session_maker):
    super_admin = await _create_user(session_maker, UserRole.SUPER_ADMIN)
    token = await _login(client, super_admin.email)

    r = await client.post(
        "/api/admins/",
        json={"email": f"rp{uuid4().hex[:6]}@x.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    admin_id = r.json()["user"]["id"]

    r2 = await client.post(
        f"/api/admins/{admin_id}/reset-password",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert "temporary_password" in r2.json()


async def test_delete_admin_requires_super_admin(client: AsyncClient, session_maker):
    admin = await _create_user(session_maker, UserRole.ADMIN)
    target = await _create_user(session_maker, UserRole.ADMIN)
    admin_token = await _login(client, admin.email)

    r = await client.delete(
        f"/api/admins/{target.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 403


async def test_audit_log_accessible_by_super_admin(client: AsyncClient, session_maker):
    super_admin = await _create_user(session_maker, UserRole.SUPER_ADMIN)
    token = await _login(client, super_admin.email)

    r = await client.get("/api/admins/audit", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body


async def test_audit_log_forbidden_for_admin(client: AsyncClient, session_maker):
    admin = await _create_user(session_maker, UserRole.ADMIN)
    token = await _login(client, admin.email)

    r = await client.get("/api/admins/audit", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


async def test_force_logout_204(client: AsyncClient, session_maker):
    super_admin = await _create_user(session_maker, UserRole.SUPER_ADMIN)
    token = await _login(client, super_admin.email)

    r = await client.post(
        "/api/admins/",
        json={"email": f"tgt{uuid4().hex[:6]}@x.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    admin_id = r.json()["user"]["id"]

    r2 = await client.post(
        f"/api/admins/{admin_id}/force-logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 204
