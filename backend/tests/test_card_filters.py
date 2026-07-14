import pytest
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.models.auth import UserCreate, UserRole

_CARD_PAYLOAD = {
    "last_name": "Тест",
    "first_name": "Иван",
    "membership_no": "MBR-FLT-001",
    "category_id": 1,
}


@pytest.fixture
async def super_headers(client: AsyncClient, user_repo):
    pw = "super#PassFLT1"
    await user_repo.create(
        UserCreate(
            email="flt_super@x.com",
            password_hash=hash_password(pw),
            role=UserRole.SUPER_ADMIN,
        )
    )
    r = await client.post("/api/auth/login", json={"email": "flt_super@x.com", "password": pw})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_list_cards_invalid_date_field(client: AsyncClient, super_headers):
    r = await client.get("/api/cards/?date_field=garbage", headers=super_headers)
    assert r.status_code == 400


async def test_list_cards_date_from_after_to(client: AsyncClient, super_headers):
    r = await client.get(
        "/api/cards/?date_from=2026-12-31&date_to=2026-01-01",
        headers=super_headers,
    )
    assert r.status_code == 400


@pytest.mark.parametrize("date_field", ["added", "opened", "modified", "created", "issued"])
async def test_list_cards_date_field_accepted(
    client: AsyncClient, super_headers, date_field: str
):
    await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=super_headers)
    r = await client.get(
        f"/api/cards/?date_field={date_field}&date_from=2020-01-01&date_to=2030-01-01",
        headers=super_headers,
    )
    assert r.status_code == 200
    assert r.json()["total"] >= 1
