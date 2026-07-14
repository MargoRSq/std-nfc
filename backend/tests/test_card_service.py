from uuid import uuid4

import pytest

from std_cards.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.category_repo import CategoryRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole
from std_cards.models.card import CardCreate, CardsListFilter, CardUpdate
from std_cards.services.card_service import CardService
from std_cards.services.slug_service import SlugService


@pytest.fixture
def card_repo(session_maker) -> CardRepository:
    return CardRepository(session_maker)


@pytest.fixture
def cat_repo(session_maker) -> CategoryRepository:
    return CategoryRepository(session_maker)


@pytest.fixture
def slug_service(card_repo) -> SlugService:
    return SlugService(card_repo)


@pytest.fixture
def svc(card_repo, slug_service, cat_repo) -> CardService:
    return CardService(card_repo, slug_service, cat_repo)


async def _make_user(session_maker):
    repo = UserRepository(session_maker)
    return await repo.create(
        UserCreate(email=f"u{uuid4().hex[:6]}@x.com", password_hash="h", role=UserRole.ADMIN)
    )


def _base_create(category_id: int = 1, **kwargs) -> CardCreate:
    kwargs.setdefault("membership_no", f"X{uuid4().hex[:8]}")
    return CardCreate(
        last_name="Тест",
        first_name="Тестович",
        category_id=category_id,
        **kwargs,
    )


async def test_create_duplicate_membership_no_raises_conflict(session_maker, svc):
    user = await _make_user(session_maker)
    await svc.create(_base_create(membership_no="DUP001"), created_by=user.id)
    with pytest.raises(ConflictError):
        await svc.create(_base_create(membership_no="DUP001"), created_by=user.id)


async def test_create_duplicate_membership_no_case_insensitive(session_maker, svc):
    user = await _make_user(session_maker)
    await svc.create(_base_create(membership_no="abc-1"), created_by=user.id)
    with pytest.raises(ConflictError):
        await svc.create(_base_create(membership_no=" ABC-1 "), created_by=user.id)


async def test_update_to_existing_membership_no_raises_conflict(session_maker, svc):
    user = await _make_user(session_maker)
    await svc.create(_base_create(membership_no="A100"), created_by=user.id)
    other = await svc.create(_base_create(membership_no="A101"), created_by=user.id)
    with pytest.raises(ConflictError):
        await svc.update(other.id, CardUpdate(membership_no="A100"))


async def test_update_same_membership_no_allowed(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(membership_no="A200"), created_by=user.id)
    updated = await svc.update(card.id, CardUpdate(membership_no="A200"))
    assert updated.membership_no == "A200"


async def test_create_allowed_after_soft_delete(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(membership_no="A300"), created_by=user.id)
    await svc.delete(card.id)
    new_card = await svc.create(_base_create(membership_no="A300"), created_by=user.id)
    assert new_card.membership_no == "A300"


async def test_create_generates_slug(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(), created_by=user.id)
    assert len(card.public_slug) >= 6
    assert card.last_name == "Тест"


async def test_create_with_custom_slug(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(public_slug="MySlug1"), created_by=user.id)
    assert card.public_slug == "MySlug1"


async def test_create_duplicate_slug_raises_conflict(session_maker, svc):
    user = await _make_user(session_maker)
    await svc.create(_base_create(public_slug="MySlug2"), created_by=user.id)
    with pytest.raises(ConflictError):
        await svc.create(_base_create(public_slug="MySlug2"), created_by=user.id)


async def test_create_invalid_category_raises_validation(session_maker, svc):
    user = await _make_user(session_maker)
    with pytest.raises(ValidationFailedError):
        await svc.create(_base_create(999), created_by=user.id)


async def test_get_not_found(svc):
    with pytest.raises(NotFoundError):
        await svc.get(uuid4())


async def test_update(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(), created_by=user.id)
    updated = await svc.update(card.id, CardUpdate(last_name="Обновлён"))
    assert updated.last_name == "Обновлён"


async def test_update_not_found(svc):
    with pytest.raises(NotFoundError):
        await svc.update(uuid4(), CardUpdate(last_name="X"))


async def test_delete(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(), created_by=user.id)
    await svc.delete(card.id)
    with pytest.raises(NotFoundError):
        await svc.get(card.id)


async def test_delete_not_found(svc):
    with pytest.raises(NotFoundError):
        await svc.delete(uuid4())


async def test_regenerate_slug(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(), created_by=user.id)
    old_slug = card.public_slug
    new_slug = await svc.regenerate_slug(card.id)
    assert new_slug != old_slug


async def test_regenerate_slug_custom(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(), created_by=user.id)
    new_slug = await svc.regenerate_slug(card.id, custom="custom7")
    assert new_slug == "custom7"


async def test_check_slug_available(svc):
    result = await svc.check_slug("freesl1")
    assert result is True


async def test_check_slug_taken(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(public_slug="taken001"), created_by=user.id)
    result = await svc.check_slug("taken001")
    assert result is False
    result_exclude = await svc.check_slug("taken001", exclude_id=card.id)
    assert result_exclude is True


async def test_check_slug_invalid_format(svc):
    result = await svc.check_slug("ab")
    assert result is False


async def test_list(session_maker, svc):
    user = await _make_user(session_maker)
    await svc.create(_base_create(), created_by=user.id)
    await svc.create(_base_create(), created_by=user.id)
    result = await svc.list(CardsListFilter())
    assert result.total == 2
    assert result.page == 1


async def test_create_defaults_logo_key_to_std_preset(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(), created_by=user.id)
    assert card.logo_key == "preset:std"


async def test_create_with_explicit_preset_unchanged(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(
        _base_create(logo_key="preset:std"), created_by=user.id
    )
    assert card.logo_key == "preset:std"


async def test_update_can_set_preset_and_clear(session_maker, svc):
    user = await _make_user(session_maker)
    card = await svc.create(_base_create(), created_by=user.id)
    cleared = await svc.update(card.id, CardUpdate(logo_key=None))
    assert cleared.logo_key is None
    reset = await svc.update(card.id, CardUpdate(logo_key="preset:std"))
    assert reset.logo_key == "preset:std"
