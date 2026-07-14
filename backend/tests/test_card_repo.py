from uuid import uuid4

from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole
from std_cards.models.card import CardCreate, CardsListFilter, CardUpdate


async def _make_user(session_maker):
    repo = UserRepository(session_maker)
    return await repo.create(
        UserCreate(email=f"u{uuid4().hex[:6]}@x.com", password_hash="h", role=UserRole.ADMIN)
    )


def _make_create(category_id: int = 1, **kwargs) -> CardCreate:
    return CardCreate(
        last_name="Иванов",
        first_name="Иван",
        membership_no="MBR-001",
        category_id=category_id,
        **kwargs,
    )


async def test_create_and_get_by_id(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    card = await repo.create(_make_create(), slug="testsl1", created_by=user.id)
    assert card.public_slug == "testsl1"
    assert card.last_name == "Иванов"

    fetched = await repo.get_by_id(card.id)
    assert fetched is not None
    assert fetched.id == card.id


async def test_get_by_slug(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    card = await repo.create(_make_create(), slug="slug001", created_by=user.id)

    fetched = await repo.get_by_slug("slug001")
    assert fetched is not None
    assert fetched.id == card.id

    not_found = await repo.get_by_slug("missing0")
    assert not_found is None


async def test_list_all(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    await repo.create(_make_create(category_id=1), slug="listA001", created_by=user.id)
    await repo.create(_make_create(category_id=2), slug="listB002", created_by=user.id)

    items, total = await repo.list(CardsListFilter())
    assert total == 2
    assert len(items) == 2


async def test_list_filter_by_category(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    await repo.create(_make_create(category_id=1), slug="cat1aaA", created_by=user.id)
    await repo.create(_make_create(category_id=2), slug="cat2bbB", created_by=user.id)

    items, total = await repo.list(CardsListFilter(category_id=1))
    assert total == 1
    assert items[0].public_slug == "cat1aaA"


async def test_list_filter_by_q(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    await repo.create(
        CardCreate(last_name="Петров", first_name="Пётр", membership_no="1", category_id=1),
        slug="petrov1",
        created_by=user.id,
    )
    await repo.create(
        CardCreate(last_name="Сидоров", first_name="Сидор", membership_no="2", category_id=1),
        slug="sidorov2",
        created_by=user.id,
    )

    items, total = await repo.list(CardsListFilter(q="петров"))
    assert total == 1
    assert items[0].last_name == "Петров"


async def test_list_pagination(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    for i in range(5):
        await repo.create(
            _make_create(),
            slug=f"page{i:04d}",
            created_by=user.id,
        )

    items, total = await repo.list(CardsListFilter(page=1, page_size=2))
    assert total == 5
    assert len(items) == 2

    items2, _ = await repo.list(CardsListFilter(page=2, page_size=2))
    assert len(items2) == 2

    items3, _ = await repo.list(CardsListFilter(page=3, page_size=2))
    assert len(items3) == 1


async def test_update_partial(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    card = await repo.create(_make_create(), slug="upd0001", created_by=user.id)

    updated = await repo.update(card.id, CardUpdate(last_name="Обновлённый", first_name="Иван"))
    assert updated is not None
    assert updated.last_name == "Обновлённый"
    assert updated.first_name == "Иван"


async def test_soft_delete(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    card = await repo.create(_make_create(), slug="del0001", created_by=user.id)

    ok = await repo.soft_delete(card.id)
    assert ok is True

    not_visible = await repo.get_by_id(card.id)
    assert not_visible is None

    visible_with_deleted = await repo.get_by_id(card.id, include_deleted=True)
    assert visible_with_deleted is not None
    assert visible_with_deleted.deleted_at is not None

    _, total = await repo.list(CardsListFilter())
    assert total == 0


async def test_soft_delete_not_in_list(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    card = await repo.create(_make_create(), slug="dli0001", created_by=user.id)
    await repo.soft_delete(card.id)

    items, total = await repo.list(CardsListFilter())
    assert total == 0
    assert items == []


async def test_slug_exists(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)

    assert await repo.slug_exists("nothere") is False
    await repo.create(_make_create(), slug="exists1", created_by=user.id)
    assert await repo.slug_exists("exists1") is True


async def test_update_slug(session_maker):
    user = await _make_user(session_maker)
    repo = CardRepository(session_maker)
    card = await repo.create(_make_create(), slug="oldslug", created_by=user.id)

    await repo.update_slug(card.id, "newslug")

    updated = await repo.get_by_slug("newslug")
    assert updated is not None
    assert updated.id == card.id

    old = await repo.get_by_slug("oldslug")
    assert old is None
