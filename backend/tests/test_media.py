import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

from std_cards.core.security import hash_password
from std_cards.infrastructure.minio import MinioClient
from std_cards.infrastructure.repositories import CardRepository
from std_cards.models.auth import UserCreate, UserRole
from std_cards.services.media_service import MediaService


def _make_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (200, 200), color=(100, 149, 237))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    img = Image.new("RGBA", (300, 300), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
async def admin_token(client: AsyncClient, user_repo):
    pw = "Media#Pass1"
    await user_repo.create(
        UserCreate(email="media_admin@x.com", password_hash=hash_password(pw), role=UserRole.ADMIN)
    )
    r = await client.post("/api/auth/login", json={"email": "media_admin@x.com", "password": pw})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
async def card_id(client: AsyncClient, auth_headers):
    r = await client.post(
        "/api/cards/",
        json={"last_name": "Фото", "first_name": "Тест", "membership_no": "MED-001", "category_id": 1},
        headers=auth_headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture
def mock_minio():
    minio = MagicMock(spec=MinioClient)
    minio.upload = AsyncMock(return_value=None)
    minio.download = AsyncMock(return_value=_make_jpeg_bytes())
    return minio


async def test_upload_photo_returns_key_and_get_media_200(
    client: AsyncClient, auth_headers, card_id, mock_minio
):
    with patch("std_cards.api.deps.get_minio", return_value=mock_minio):
        r = await client.post(
            f"/api/cards/{card_id}/photo",
            headers=auth_headers,
            files={"file": ("photo.jpg", _make_jpeg_bytes(), "image/jpeg")},
        )
    assert r.status_code == 200
    body = r.json()
    assert "photo_key" in body
    assert body["photo_key"].startswith(f"cards/{card_id}/photo-")
    assert body["photo_key"].endswith(".webp")

    key = body["photo_key"]
    with patch("std_cards.api.deps.get_minio", return_value=mock_minio):
        r2 = await client.get(f"/api/media/{key}")
    assert r2.status_code == 200
    assert r2.headers["content-type"].startswith("image/webp")


async def test_upload_photo_no_auth(client: AsyncClient, card_id):
    r = await client.post(
        f"/api/cards/{card_id}/photo",
        files={"file": ("photo.jpg", _make_jpeg_bytes(), "image/jpeg")},
    )
    assert r.status_code == 401


async def test_upload_photo_nonexistent_card(client: AsyncClient, auth_headers, mock_minio):
    fake_id = uuid4()
    with patch("std_cards.api.deps.get_minio", return_value=mock_minio):
        r = await client.post(
            f"/api/cards/{fake_id}/photo",
            headers=auth_headers,
            files={"file": ("photo.jpg", _make_jpeg_bytes(), "image/jpeg")},
        )
    assert r.status_code == 404


async def test_upload_invalid_image_type(client: AsyncClient, auth_headers, card_id, mock_minio):
    with patch("std_cards.api.deps.get_minio", return_value=mock_minio):
        r = await client.post(
            f"/api/cards/{card_id}/photo",
            headers=auth_headers,
            files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code == 422


async def test_upload_logo_returns_logo_key(client: AsyncClient, auth_headers, card_id, mock_minio):
    with patch("std_cards.api.deps.get_minio", return_value=mock_minio):
        r = await client.post(
            f"/api/cards/{card_id}/logo",
            headers=auth_headers,
            files={"file": ("logo.png", _make_png_bytes(), "image/png")},
        )
    assert r.status_code == 200
    body = r.json()
    assert "logo_key" in body
    assert body["logo_key"].startswith(f"cards/{card_id}/logo-")


async def test_media_service_stream_not_found(session_maker):
    minio = MagicMock(spec=MinioClient)
    minio.download = AsyncMock(side_effect=Exception("key not found"))
    card_repo = CardRepository(session_maker)
    svc = MediaService(minio, card_repo)

    from std_cards.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await svc.stream_media("nonexistent/key.webp")
