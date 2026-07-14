import pytest

from std_cards.core.security import hash_password
from std_cards.infrastructure.repositories import (
    CardRepository,
    TemplateRepository,
)
from std_cards.models.auth import UserCreate, UserRole
from std_cards.models.card import CardCreate
from std_cards.models.template import TemplateCreate, TemplateUpdate
from std_cards.services.template_service import TemplateService


@pytest.fixture
def template_repo(session_maker):
    return TemplateRepository(session_maker)


@pytest.fixture
def card_repo(session_maker):
    return CardRepository(session_maker)


@pytest.fixture
async def admin_user(user_repo):
    return await user_repo.create(
        UserCreate(
            email="tpl_admin@x.com",
            password_hash=hash_password("Pass#1234"),
            role=UserRole.ADMIN,
        )
    )


@pytest.fixture
def template_service(template_repo, card_repo, category_repo):
    return TemplateService(template_repo, card_repo, category_repo)


async def test_create_and_list(template_service, admin_user):
    tpl = await template_service.create(
        TemplateCreate(name="Test Template", category_id=1),
        created_by=admin_user.id,
    )
    assert tpl.name == "Test Template"
    assert tpl.category_id == 1

    all_tpl = await template_service.list_all()
    assert any(t.id == tpl.id for t in all_tpl)


async def test_get(template_service, admin_user):
    tpl = await template_service.create(
        TemplateCreate(name="GetMe", category_id=1),
        created_by=admin_user.id,
    )
    fetched = await template_service.get(tpl.id)
    assert fetched.id == tpl.id
    assert fetched.name == "GetMe"


async def test_update(template_service, admin_user):
    tpl = await template_service.create(
        TemplateCreate(name="OldName", category_id=1),
        created_by=admin_user.id,
    )
    updated = await template_service.update(tpl.id, TemplateUpdate(name="NewName"))
    assert updated.name == "NewName"
    assert updated.id == tpl.id


async def test_delete(template_service, admin_user):
    from std_cards.core.exceptions import NotFoundError

    tpl = await template_service.create(
        TemplateCreate(name="ToDelete", category_id=1),
        created_by=admin_user.id,
    )
    await template_service.delete(tpl.id)
    with pytest.raises(NotFoundError):
        await template_service.get(tpl.id)


async def test_duplicate(template_service, admin_user):
    tpl = await template_service.create(
        TemplateCreate(
            name="Original",
            category_id=1,
            default_styles={"bg_kind": "solid"},
        ),
        created_by=admin_user.id,
    )
    dup = await template_service.duplicate(tpl.id, "Copy of Original")
    assert dup.name == "Copy of Original"
    assert dup.default_styles == tpl.default_styles
    assert dup.id != tpl.id


async def test_from_card(template_service, card_repo, admin_user):
    card = await card_repo.create(
        CardCreate(
            last_name="Иванов",
            first_name="Иван",
            membership_no="MBR-999",
            category_id=1,
            bg_kind="solid",
            bg_color="#FF0000",
            photo_shape="circle",
        ),
        slug="test-slug1",
        created_by=admin_user.id,
    )
    tpl = await template_service.from_card(card.id, "From Card", created_by=admin_user.id)
    assert tpl.name == "From Card"
    assert tpl.category_id == 1
    assert tpl.default_styles.get("bg_kind") == "solid"
    assert tpl.default_styles.get("bg_color") == "#FF0000"
    assert tpl.default_styles.get("photo_shape") == "circle"
