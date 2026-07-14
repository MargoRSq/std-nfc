from httpx import AsyncClient

from std_cards.core.ratelimit import not_found_burst_lockout
from std_cards.core.security import hash_password
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole
from std_cards.models.card import CardCreate, CardUpdate


async def test_public_card_renders_html(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="a@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(
            last_name="Иванов",
            first_name="Иван",
            membership_no="123",
            category_id=1,
            region="Москва",
        ),
        slug="test01",
        created_by=admin.id,
    )
    r = await client.get("/c/test01")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "noindex" in r.headers["x-robots-tag"]
    assert "Иванов" in r.text
    assert "Иван" in r.text


async def test_public_card_404_for_unknown(client: AsyncClient):
    r = await client.get("/c/notexist")
    assert r.status_code == 404
    assert "noindex" in r.headers["x-robots-tag"]


async def test_public_card_410_when_inactive(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="a2@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    card = await card_repo.create(
        CardCreate(last_name="Sad", first_name="Test", membership_no="X", category_id=1),
        slug="inact1",
        created_by=admin.id,
    )
    await card_repo.update(card.id, CardUpdate(is_active=False))
    r = await client.get("/c/inact1")
    assert r.status_code == 410


async def test_public_card_robots_blocked(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="a3@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(last_name="Y", first_name="Z", membership_no="A", category_id=1),
        slug="rbts01",
        created_by=admin.id,
    )
    r = await client.get("/c/rbts01", headers={"User-Agent": "Googlebot/2.1"})
    assert r.status_code == 200
    assert "noindex" in r.headers["x-robots-tag"].lower()


async def test_burst_lockout_after_404_threshold(client: AsyncClient):
    original_threshold = not_found_burst_lockout._threshold
    original_block = not_found_burst_lockout._block_seconds
    not_found_burst_lockout._threshold = 3
    not_found_burst_lockout._block_seconds = 5
    try:
        for _ in range(3):
            await client.get("/c/missing-slug")
        r = await client.get("/c/another-missing")
        assert r.status_code == 429
    finally:
        not_found_burst_lockout._threshold = original_threshold
        not_found_burst_lockout._block_seconds = original_block
        async with not_found_burst_lockout._lock:
            not_found_burst_lockout._hits.clear()
            not_found_burst_lockout._blocked_until.clear()


async def test_public_card_renders_preset_logo_url(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="logo1@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(
            last_name="P",
            first_name="P",
            membership_no="L1",
            category_id=1,
            logo_key="preset:std",
        ),
        slug="logo1x",
        created_by=admin.id,
    )
    r = await client.get("/c/logo1x")
    assert r.status_code == 200
    assert 'src="/logos/std.png"' in r.text
    assert "/api/media/preset:std" not in r.text


async def test_public_card_renders_uploaded_logo_url(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="logo2@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    card = await card_repo.create(
        CardCreate(last_name="P", first_name="P", membership_no="L2", category_id=1),
        slug="logo2x",
        created_by=admin.id,
    )
    await card_repo.set_logo_key(card.id, "cards/abc/logo-feedface.webp")
    r = await client.get("/c/logo2x")
    assert r.status_code == 200
    assert 'src="/api/media/cards/abc/logo-feedface.webp"' in r.text
    assert "/logos/" not in r.text


async def test_public_card_falls_back_to_brand_when_logo_null(
    client: AsyncClient, session_maker
):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="logo3@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    card = await card_repo.create(
        CardCreate(last_name="P", first_name="P", membership_no="L3", category_id=1),
        slug="logo3x",
        created_by=admin.id,
    )
    await card_repo.update(card.id, CardUpdate(logo_key=None))
    r = await client.get("/c/logo3x")
    assert r.status_code == 200
    assert "std-logo-full" in r.text


async def test_feedback_endpoint_204_for_valid(client: AsyncClient, session_maker):
    user_repo = UserRepository(session_maker)
    card_repo = CardRepository(session_maker)
    admin = await user_repo.create(
        UserCreate(email="a4@x.com", password_hash=hash_password("p"), role=UserRole.ADMIN)
    )
    await card_repo.create(
        CardCreate(last_name="Fb", first_name="Test", membership_no="F", category_id=1),
        slug="fbk001",
        created_by=admin.id,
    )
    r = await client.post(
        "/api/public/cards/fbk001/feedback",
        json={"name": "Иван", "contact": "test@x.com", "message": "Добрый день"},
    )
    assert r.status_code == 204
