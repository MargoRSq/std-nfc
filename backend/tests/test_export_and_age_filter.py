import io
from datetime import date

import openpyxl
import pytest
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.models.auth import UserCreate, UserRole


@pytest.fixture
async def super_headers(client: AsyncClient, user_repo):
    pw = "super#PassExp1"
    await user_repo.create(
        UserCreate(
            email="export_super@x.com",
            password_hash=hash_password(pw),
            role=UserRole.SUPER_ADMIN,
        )
    )
    r = await client.post("/api/auth/login", json={"email": "export_super@x.com", "password": pw})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _rows(content: bytes) -> list[tuple]:
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    return list(wb.active.iter_rows(values_only=True))


async def _create(client: AsyncClient, headers, **overrides):
    payload = {
        "last_name": "Тест",
        "first_name": "Иван",
        "membership_no": "MBR-EXP-000",
        "category_id": 1,
    } | overrides
    r = await client.post("/api/cards/", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def test_export_respects_category_filter(client: AsyncClient, super_headers):
    await _create(client, super_headers, membership_no="MBR-EXP-CAT1", category_id=1)
    await _create(client, super_headers, membership_no="MBR-EXP-CAT2", category_id=2)

    r = await client.get("/api/cards/export.xlsx?category_id=2", headers=super_headers)
    assert r.status_code == 200
    rows = _rows(r.content)
    assert len(rows) == 2  # заголовок + одна карточка выбранной категории
    assert rows[1][5] == "MBR-EXP-CAT2"


async def test_export_includes_service_fields(client: AsyncClient, super_headers):
    await _create(
        client,
        super_headers,
        membership_no="MBR-EXP-SRV",
        exclusion_year=2026,
        death_date="2026-03-01",
    )
    r = await client.get("/api/cards/export.xlsx", headers=super_headers)
    header, row = _rows(r.content)[:2]
    assert "Год исключения из СТД" in header
    assert "Дата смерти" in header
    assert row[header.index("Год исключения из СТД")] == 2026
    assert row[header.index("Дата смерти")] == "2026-03-01"


async def test_age_filter_selects_by_birth_date(client: AsyncClient, super_headers):
    today = date.today()
    young = today.replace(year=today.year - 30).isoformat()
    old = today.replace(year=today.year - 70).isoformat()
    await _create(client, super_headers, membership_no="MBR-AGE-30", birth_date=young)
    await _create(client, super_headers, membership_no="MBR-AGE-70", birth_date=old)

    r = await client.get("/api/cards/?age_from=60", headers=super_headers)
    assert r.status_code == 200
    assert [i["membership_no"] for i in r.json()["items"]] == ["MBR-AGE-70"]

    r = await client.get("/api/cards/?age_to=40", headers=super_headers)
    assert [i["membership_no"] for i in r.json()["items"]] == ["MBR-AGE-30"]

    r = await client.get("/api/cards/?age_from=20&age_to=80", headers=super_headers)
    assert r.json()["total"] == 2


async def test_age_filter_rejects_inverted_range(client: AsyncClient, super_headers):
    r = await client.get("/api/cards/?age_from=60&age_to=20", headers=super_headers)
    assert r.status_code == 422


async def test_export_age_filter(client: AsyncClient, super_headers):
    today = date.today()
    await _create(
        client,
        super_headers,
        membership_no="MBR-EXPAGE-25",
        birth_date=today.replace(year=today.year - 25).isoformat(),
    )
    await _create(
        client,
        super_headers,
        membership_no="MBR-EXPAGE-80",
        birth_date=today.replace(year=today.year - 80).isoformat(),
    )
    r = await client.get("/api/cards/export.xlsx?age_from=70", headers=super_headers)
    rows = _rows(r.content)
    assert len(rows) == 2
    assert rows[1][5] == "MBR-EXPAGE-80"
