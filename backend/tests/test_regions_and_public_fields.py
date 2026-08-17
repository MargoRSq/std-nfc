from datetime import date

import pytest
from httpx import AsyncClient

from std_cards.core.security import hash_password
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole
from std_cards.models.card import CardCreate, ContactBlock


@pytest.fixture
async def super_headers(client: AsyncClient, user_repo):
    pw = "super#PassReg1"
    await user_repo.create(
        UserCreate(
            email="regions_super@x.com",
            password_hash=hash_password(pw),
            role=UserRole.SUPER_ADMIN,
        )
    )
    r = await client.post("/api/auth/login", json={"email": "regions_super@x.com", "password": pw})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create(client: AsyncClient, headers, **overrides):
    payload = {
        "last_name": "Тест",
        "first_name": "Иван",
        "membership_no": "MBR-REG-000",
        "category_id": 1,
    } | overrides
    r = await client.post("/api/cards/", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def test_regions_endpoint_lists_only_used_regions(client: AsyncClient, super_headers):
    await _create(client, super_headers, membership_no="R-1", region="Москва")
    await _create(client, super_headers, membership_no="R-2", region="Москва")
    await _create(client, super_headers, membership_no="R-3", region="Тверская область")
    await _create(client, super_headers, membership_no="R-4")

    r = await client.get("/api/cards/regions", headers=super_headers)
    assert r.status_code == 200
    by_region = {item["region"]: item["cards_count"] for item in r.json()}
    assert by_region == {"Москва": 2, "Тверская область": 1}


async def test_region_filter_narrows_list(client: AsyncClient, super_headers):
    await _create(client, super_headers, membership_no="RF-1", region="Москва")
    await _create(client, super_headers, membership_no="RF-2", region="Тверская область")

    r = await client.get("/api/cards/?region=Москва", headers=super_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1


async def test_public_card_shows_exclusion_year_only_when_set(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="excl@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(last_name="Исключён", first_name="Пётр", membership_no="E-1", category_id=1),
        slug="exclu1",
        created_by=admin.id,
    )
    await card_repo.create(
        CardCreate(
            last_name="Активен",
            first_name="Павел",
            membership_no="E-2",
            category_id=1,
            exclusion_year=2025,
        ),
        slug="exclu2",
        created_by=admin.id,
    )

    without = await client.get("/c/exclu1")
    assert "Дата исключения" not in without.text

    with_year = await client.get("/c/exclu2")
    assert "Дата исключения" in with_year.text
    assert "2025" in with_year.text


async def test_public_card_prefers_exclusion_date_over_year(client: AsyncClient, session_maker):
    """На билете нужна дата; год остаётся запасным вариантом для старых карточек."""
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="excl2@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(
            last_name="Сдатой",
            first_name="Игорь",
            membership_no="E-3",
            category_id=1,
            exclusion_year=2025,
            exclusion_date=date(2025, 3, 14),
        ),
        slug="exclu3",
        created_by=admin.id,
    )

    r = await client.get("/c/exclu3")
    assert "Дата исключения" in r.text
    assert "14.03.2025" in r.text


async def test_public_card_keeps_contacts_only_in_modal(client: AsyncClient, session_maker):
    """Контакты рисуются один раз — внутри модалки, а не строками на карточке."""
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="contacts@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(
            last_name="Контактов",
            first_name="Илья",
            membership_no="C-1",
            category_id=1,
            contacts=[ContactBlock(type="email", value="member@example.com")],
        ),
        slug="cont01",
        created_by=admin.id,
    )

    r = await client.get("/c/cont01")
    assert r.status_code == 200
    card_html, _, modal_html = r.text.partition('class="modal-overlay"')
    assert "member@example.com" not in card_html
    assert "member@example.com" in modal_html


async def test_public_card_hides_internal_blocks(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="internal@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(
            last_name="Служебный",
            first_name="Роман",
            membership_no="I-1",
            category_id=1,
            internal_blocks=[ContactBlock(type="phone", value="+7 (926) 946-56-59")],
        ),
        slug="intr01",
        created_by=admin.id,
    )

    r = await client.get("/c/intr01")
    assert r.status_code == 200
    assert "946-56-59" not in r.text


async def test_apply_template_writes_canonical_gradient_keys(
    client: AsyncClient, session_maker, super_headers
):
    """«Назначить шаблон» должен класть градиент в ключах from/to.

    Публичный шаблон и превью читают только их: при from_color/to_color карточка
    рисовалась дефолтным градиентом вместо цветов шаблона.
    """
    card = await _create(client, super_headers, membership_no="G-1")

    r = await client.post(
        "/api/templates/",
        json={
            "name": "Градиентный",
            "category_id": 1,
            "default_styles": {
                "bg_kind": "gradient",
                "bg_gradient": {"from": "#AA0000", "to": "#00AA00", "angle": 90},
            },
        },
        headers=super_headers,
    )
    assert r.status_code == 201, r.text
    template_id = r.json()["id"]

    r = await client.post(
        f"/api/cards/{card['id']}/apply-template",
        json={"template_id": template_id},
        headers=super_headers,
    )
    assert r.status_code == 200, r.text

    r = await client.get(f"/api/cards/{card['id']}", headers=super_headers)
    gradient = r.json()["bg_gradient"]
    assert set(gradient) >= {"from", "to"}, gradient
    assert "from_color" not in gradient
    assert "to_color" not in gradient
    assert gradient["from"] == "#AA0000"

    public = await client.get(f"/c/{r.json()['public_slug']}")
    assert "#AA0000" in public.text
    assert "#00AA00" in public.text


async def test_legacy_gradient_keys_are_normalized_on_write(client: AsyncClient, super_headers):
    card = await _create(client, super_headers, membership_no="G-2")
    r = await client.patch(
        f"/api/cards/{card['id']}",
        json={
            "bg_kind": "gradient",
            "bg_gradient": {"from": "#123456", "to": "#654321", "angle": 135},
        },
        headers=super_headers,
    )
    assert r.status_code == 200, r.text
    gradient = r.json()["bg_gradient"]
    assert gradient["from"] == "#123456"
    assert gradient["to"] == "#654321"
    assert "from_color" not in gradient
