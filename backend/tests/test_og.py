import io

import pytest
from httpx import AsyncClient
from PIL import Image

from std_cards.core.security import hash_password
from std_cards.models.auth import UserCreate, UserRole
from std_cards.services.og_service import render_card_og


def test_render_card_og_returns_png_bytes():
    card = {
        "last_name": "Иванов",
        "first_name": "Иван",
        "middle_name": "Иванович",
        "membership_no": "OG-001",
        "bg_kind": "solid",
        "bg_color": "#1F1E5E",
        "photo_shape": "square",
        "photo_key": None,
    }
    out = render_card_og(card)
    assert out[:8] == b"\x89PNG\r\n\x1a\n"
    img = Image.open(io.BytesIO(out))
    assert img.size == (1200, 630)


def test_render_card_og_with_gradient():
    card = {
        "last_name": "Петров",
        "first_name": "Пётр",
        "middle_name": None,
        "membership_no": "OG-002",
        "bg_kind": "gradient",
        "bg_gradient": {"from": "#3D2B7E", "to": "#7058D6", "angle": 135},
        "photo_shape": "square",
        "photo_key": None,
    }
    out = render_card_og(card)
    assert len(out) > 0
    assert Image.open(io.BytesIO(out)).size == (1200, 630)


def test_render_card_og_long_name_shrinks():
    card = {
        "last_name": "Иванов-Тишковецкий-Долгий",
        "first_name": "Александр",
        "middle_name": "Константинович",
        "membership_no": "OG-003",
        "bg_kind": "solid",
        "bg_color": "#1F1E5E",
        "photo_shape": "square",
        "photo_key": None,
    }
    out = render_card_og(card)
    assert Image.open(io.BytesIO(out)).size == (1200, 630)


def test_render_card_og_invalid_bg_falls_back():
    card = {
        "last_name": "T",
        "first_name": "A",
        "membership_no": "X",
        "bg_kind": "solid",
        "bg_color": "not-a-color",
        "photo_shape": "square",
    }
    out = render_card_og(card)
    assert Image.open(io.BytesIO(out)).size == (1200, 630)


_CARD_PAYLOAD = {
    "last_name": "Тест",
    "first_name": "OG",
    "membership_no": "OG-ENDPOINT-001",
    "category_id": 1,
}


@pytest.fixture
async def admin_token(client: AsyncClient, user_repo):
    pw = "admin#OGtest1"
    await user_repo.create(
        UserCreate(email="og_admin@x.com", password_hash=hash_password(pw), role=UserRole.SUPER_ADMIN)
    )
    r = await client.post("/api/auth/login", json={"email": "og_admin@x.com", "password": pw})
    assert r.status_code == 200
    return r.json()["access_token"]


async def test_og_endpoint_returns_png(client: AsyncClient, admin_token):
    r = await client.post(
        "/api/cards/", json=_CARD_PAYLOAD, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert r.status_code == 201
    slug = r.json()["public_slug"]

    r = await client.get(f"/c/{slug}/og.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"].startswith("public")
    assert "etag" in r.headers
    img = Image.open(io.BytesIO(r.content))
    assert img.size == (1200, 630)


async def test_og_endpoint_etag_304(client: AsyncClient, admin_token):
    r = await client.post(
        "/api/cards/", json=_CARD_PAYLOAD, headers={"Authorization": f"Bearer {admin_token}"}
    )
    slug = r.json()["public_slug"]
    first = await client.get(f"/c/{slug}/og.png")
    etag = first.headers["etag"]

    second = await client.get(f"/c/{slug}/og.png", headers={"If-None-Match": etag})
    assert second.status_code == 304


async def test_og_endpoint_unknown_slug_redirects(client: AsyncClient):
    r = await client.get("/c/unknown123/og.png", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/og-default.png"
