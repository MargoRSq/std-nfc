import pytest
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.models.auth import UserCreate, UserRole

_CARD_PAYLOAD = {
    "last_name": "Тест",
    "first_name": "Иван",
    "membership_no": "MBR-MSG-001",
    "category_id": 1,
}


@pytest.fixture
async def admin_token(client: AsyncClient, user_repo):
    pw = "admin#PassMSG1"
    await user_repo.create(
        UserCreate(
            email="msg_admin@x.com", password_hash=hash_password(pw), role=UserRole.SUPER_ADMIN
        )
    )
    r = await client.post("/api/auth/login", json={"email": "msg_admin@x.com", "password": pw})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


async def _create_card(client: AsyncClient, headers: dict) -> str:
    r = await client.post("/api/cards/", json=_CARD_PAYLOAD, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


async def test_publish_message_text_only(client: AsyncClient, auth_headers):
    card_id = await _create_card(client, auth_headers)
    r = await client.post(
        f"/api/cards/{card_id}/messages",
        data={"text": "Hello members"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["text"] == "Hello members"
    assert body["image_key"] is None
    assert body["card_id"] == card_id


async def test_publish_message_empty_rejected(client: AsyncClient, auth_headers):
    card_id = await _create_card(client, auth_headers)
    r = await client.post(
        f"/api/cards/{card_id}/messages",
        data={"text": "   "},
        headers=auth_headers,
    )
    assert r.status_code in (400, 422)


async def test_list_messages(client: AsyncClient, auth_headers):
    card_id = await _create_card(client, auth_headers)
    await client.post(
        f"/api/cards/{card_id}/messages", data={"text": "first"}, headers=auth_headers
    )
    await client.post(
        f"/api/cards/{card_id}/messages", data={"text": "second"}, headers=auth_headers
    )
    r = await client.get(f"/api/cards/{card_id}/messages", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    assert items[0]["text"] == "second"


async def test_soft_delete_message(client: AsyncClient, auth_headers):
    card_id = await _create_card(client, auth_headers)
    r = await client.post(
        f"/api/cards/{card_id}/messages", data={"text": "to delete"}, headers=auth_headers
    )
    msg_id = r.json()["id"]
    r2 = await client.delete(
        f"/api/cards/{card_id}/messages/{msg_id}", headers=auth_headers
    )
    assert r2.status_code == 204

    r3 = await client.get(f"/api/cards/{card_id}/messages", headers=auth_headers)
    assert r3.status_code == 200
    assert all(m["id"] != msg_id for m in r3.json())


async def test_publish_unauthenticated_rejected(client: AsyncClient, auth_headers):
    card_id = await _create_card(client, auth_headers)
    r = await client.post(
        f"/api/cards/{card_id}/messages",
        data={"text": "anonymous"},
    )
    assert r.status_code == 401


async def test_messages_for_unknown_card(client: AsyncClient, auth_headers):
    from uuid import uuid4

    r = await client.post(
        f"/api/cards/{uuid4()}/messages",
        data={"text": "ghost"},
        headers=auth_headers,
    )
    assert r.status_code == 404
