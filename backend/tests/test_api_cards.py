from uuid import uuid4

import pytest
from httpx import AsyncClient

from std_cards.core.ratelimit import login_rate_limiter
from std_cards.core.security import hash_password
from std_cards.models.auth import UserCreate, UserRole


@pytest.fixture(autouse=True)
async def _clear_rate_limiter():
    await login_rate_limiter.cleanup_expired()
    login_rate_limiter._buckets.clear()


@pytest.fixture
async def admin_token(client: AsyncClient, user_repo):
    pw = "admin#Pass1"
    await user_repo.create(
        UserCreate(email="api_admin@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    r = await client.post("/api/auth/login", json={"email": "api_admin@x.com", "password": pw})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
async def superadmin_token(client: AsyncClient, user_repo):
    pw = "super#Pass1"
    await user_repo.create(
        UserCreate(
            email="api_super@x.com",
            password_hash=hash_password(pw),
            role=UserRole.SUPER_ADMIN,
        )
    )
    r = await client.post("/api/auth/login", json={"email": "api_super@x.com", "password": pw})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def super_headers(superadmin_token):
    return {"Authorization": f"Bearer {superadmin_token}"}


_CARD_PAYLOAD = {
    "last_name": "Тест",
    "first_name": "Иван",
    "membership_no": "MBR-001",
    "category_id": 1,
}


async def test_create_card_no_auth(client: AsyncClient):
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD)
    assert r.status_code == 401


async def test_create_card_success(client: AsyncClient, auth_headers):
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["last_name"] == "Тест"
    assert len(body["public_slug"]) >= 6
    assert "id" in body


async def test_list_cards(client: AsyncClient, super_headers):
    await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    await client.post(
        "/api/cards/",
        json={**_CARD_PAYLOAD, "category_id": 2, "membership_no": "MBR-002"},
        headers=super_headers,
    )

    r = await client.get("/api/cards/", headers=super_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_list_cards_filter_category(client: AsyncClient, super_headers):
    await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    await client.post(
        "/api/cards/",
        json={**_CARD_PAYLOAD, "category_id": 2, "membership_no": "MBR-002"},
        headers=super_headers,
    )

    r = await client.get("/api/cards/?category_id=1", headers=super_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1


async def test_get_card(client: AsyncClient, super_headers):
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    card_id = r.json()["id"]

    r2 = await client.get(f"/api/cards/{card_id}", headers=super_headers)
    assert r2.status_code == 200
    assert r2.json()["id"] == card_id


async def test_get_card_not_found(client: AsyncClient, super_headers):
    r = await client.get(f"/api/cards/{uuid4()}", headers=super_headers)
    assert r.status_code == 404


async def test_patch_card(client: AsyncClient, super_headers):
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    card_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/cards/{card_id}",
        json={"last_name": "Обновлён"},
        headers=super_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["last_name"] == "Обновлён"


async def test_delete_card(client: AsyncClient, super_headers):
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    card_id = r.json()["id"]

    r2 = await client.delete(f"/api/cards/{card_id}", headers=super_headers)
    assert r2.status_code == 204

    r3 = await client.get(f"/api/cards/{card_id}", headers=super_headers)
    assert r3.status_code == 404


async def test_check_slug_available(client: AsyncClient, auth_headers):
    r = await client.get("/api/cards/check-slug?slug=freesl1", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["available"] is True


async def test_check_slug_taken(client: AsyncClient, auth_headers):
    r = await client.post(
        "/api/cards/",
        json={**_CARD_PAYLOAD, "public_slug": "takenA1"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    r2 = await client.get("/api/cards/check-slug?slug=takenA1", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["available"] is False


async def test_regenerate_slug_requires_superadmin(client: AsyncClient, super_headers, auth_headers):
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    card_id = r.json()["id"]

    r2 = await client.post(
        f"/api/cards/{card_id}/regenerate-slug",
        json={},
        headers=auth_headers,
    )
    assert r2.status_code == 403


async def test_regenerate_slug_superadmin(client: AsyncClient, super_headers):
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    card_id = r.json()["id"]
    old_slug = r.json()["public_slug"]

    r2 = await client.post(
        f"/api/cards/{card_id}/regenerate-slug",
        json={},
        headers=super_headers,
    )
    assert r2.status_code == 200
    new_slug = r2.json()["public_slug"]
    assert new_slug != old_slug


async def test_list_categories(client: AsyncClient, auth_headers):
    r = await client.get("/api/categories/", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 4
    codes = [c["code"] for c in body]
    assert "platinum" in codes
    assert "gold" in codes
    assert "silver" in codes
    assert "bronze" in codes
