from uuid import uuid4

import pytest
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.models.auth import UserCreate, UserRole


@pytest.fixture
async def admin_token(client: AsyncClient, user_repo):
    pw = "Tpl#Pass1"
    await user_repo.create(
        UserCreate(
            email="tpl_api_admin@x.com",
            password_hash=hash_password(pw),
            role=UserRole.ADMIN,
        )
    )
    r = await client.post("/api/auth/login", json={"email": "tpl_api_admin@x.com", "password": pw})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


_TPL_PAYLOAD = {
    "name": "Test Template",
    "category_id": 1,
    "default_fields": {},
    "default_styles": {},
    "custom_field_schema": [],
}


async def test_create_template(client: AsyncClient, auth_headers):
    r = await client.post("/api/templates/", json=_TPL_PAYLOAD, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Test Template"
    assert "id" in body


async def test_list_templates(client: AsyncClient, auth_headers):
    await client.post("/api/templates/", json=_TPL_PAYLOAD, headers=auth_headers)
    await client.post(
        "/api/templates/",
        json={**_TPL_PAYLOAD, "name": "Second Template", "category_id": 2},
        headers=auth_headers,
    )
    r = await client.get("/api/templates/", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_get_template(client: AsyncClient, auth_headers):
    r = await client.post("/api/templates/", json=_TPL_PAYLOAD, headers=auth_headers)
    tpl_id = r.json()["id"]

    r2 = await client.get(f"/api/templates/{tpl_id}", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["id"] == tpl_id


async def test_get_template_not_found(client: AsyncClient, auth_headers):
    r = await client.get(f"/api/templates/{uuid4()}", headers=auth_headers)
    assert r.status_code == 404


async def test_patch_template(client: AsyncClient, auth_headers):
    r = await client.post("/api/templates/", json=_TPL_PAYLOAD, headers=auth_headers)
    tpl_id = r.json()["id"]

    r2 = await client.patch(
        f"/api/templates/{tpl_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "Updated Name"


async def test_delete_template(client: AsyncClient, auth_headers):
    r = await client.post("/api/templates/", json=_TPL_PAYLOAD, headers=auth_headers)
    tpl_id = r.json()["id"]

    r2 = await client.delete(f"/api/templates/{tpl_id}", headers=auth_headers)
    assert r2.status_code == 200
    assert "cards_deleted" in r2.json()

    r3 = await client.get(f"/api/templates/{tpl_id}", headers=auth_headers)
    assert r3.status_code == 404


async def test_duplicate_template(client: AsyncClient, auth_headers):
    r = await client.post("/api/templates/", json=_TPL_PAYLOAD, headers=auth_headers)
    tpl_id = r.json()["id"]

    r2 = await client.post(
        f"/api/templates/{tpl_id}/duplicate",
        json={"new_name": "Copy of Test"},
        headers=auth_headers,
    )
    assert r2.status_code == 201
    body = r2.json()
    assert body["name"] == "Copy of Test"
    assert body["id"] != tpl_id


async def test_from_card_creates_template(client: AsyncClient, auth_headers):
    card_r = await client.post(
        "/api/cards/",
        json={
            "last_name": "Карточкин",
            "first_name": "Иван",
            "membership_no": "MBR-TPL-001",
            "category_id": 1,
            "bg_kind": "solid",
            "bg_color": "#123456",
        },
        headers=auth_headers,
    )
    assert card_r.status_code == 201
    card_id = card_r.json()["id"]

    r = await client.post(
        f"/api/templates/from-card/{card_id}",
        json={"name": "From Card Template"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "From Card Template"
    assert body["default_styles"]["bg_kind"] == "solid"
    assert body["default_styles"]["bg_color"] == "#123456"


async def test_create_template_no_auth(client: AsyncClient):
    r = await client.post("/api/templates/", json=_TPL_PAYLOAD)
    assert r.status_code == 401
