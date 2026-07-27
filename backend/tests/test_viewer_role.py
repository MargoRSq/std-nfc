import pytest
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.models.auth import UserCreate, UserRole

_CARD_PAYLOAD = {
    "last_name": "Тест",
    "first_name": "Пётр",
    "membership_no": "MBR-VIEW-001",
    "category_id": 1,
}


@pytest.fixture
async def viewer_headers(client: AsyncClient, user_repo):
    pw = "viewer#Pass1"
    await user_repo.create(
        UserCreate(email="viewer@x.com", password_hash=hash_password(pw), role=UserRole.VIEWER)
    )
    r = await client.post("/api/auth/login", json={"email": "viewer@x.com", "password": pw})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def super_headers(client: AsyncClient, user_repo):
    pw = "super#PassV1"
    await user_repo.create(
        UserCreate(
            email="viewer_super@x.com",
            password_hash=hash_password(pw),
            role=UserRole.SUPER_ADMIN,
        )
    )
    r = await client.post("/api/auth/login", json={"email": "viewer_super@x.com", "password": pw})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_viewer_can_read_cards(client: AsyncClient, viewer_headers, super_headers):
    created = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    assert created.status_code == 201
    card_id = created.json()["id"]

    listing = await client.get("/api/cards/", headers=viewer_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    single = await client.get(f"/api/cards/{card_id}", headers=viewer_headers)
    assert single.status_code == 200


async def test_viewer_sees_all_cards_regardless_of_categories(
    client: AsyncClient, viewer_headers, super_headers
):
    for idx, category_id in enumerate((1, 2), start=1):
        payload = _CARD_PAYLOAD | {"membership_no": f"MBR-VIEW-CAT{idx}", "category_id": category_id}
        assert (
            await client.post("/api/cards/", json=payload, headers=super_headers)
        ).status_code == 201

    listing = await client.get("/api/cards/", headers=viewer_headers)
    assert listing.json()["total"] == 2


async def test_viewer_can_export(client: AsyncClient, viewer_headers):
    r = await client.get("/api/cards/export.xlsx", headers=viewer_headers)
    assert r.status_code == 200


async def test_viewer_can_read_analytics_and_categories(client: AsyncClient, viewer_headers):
    assert (await client.get("/api/categories/", headers=viewer_headers)).status_code == 200
    assert (
        await client.get("/api/analytics/dashboard", headers=viewer_headers)
    ).status_code == 200


async def test_viewer_cannot_write(client: AsyncClient, viewer_headers, super_headers):
    created = await client.post(
        "/api/cards/",
        json=_CARD_PAYLOAD | {"membership_no": "MBR-VIEW-RO"},
        headers=super_headers,
    )
    card_id = created.json()["id"]

    assert (
        await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=viewer_headers)
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/cards/{card_id}", json={"last_name": "Новый"}, headers=viewer_headers
        )
    ).status_code == 403
    assert (await client.delete(f"/api/cards/{card_id}", headers=viewer_headers)).status_code == 403
    assert (
        await client.post("/api/templates/", json={"name": "X"}, headers=viewer_headers)
    ).status_code == 403
