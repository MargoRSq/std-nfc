from uuid import uuid4

from std_cards.infrastructure.repositories.admin_card_groups_repo import AdminCardGroupRepository
from std_cards.infrastructure.repositories.card_repo import CardRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.auth import UserCreate, UserRole
from std_cards.models.card import CardCreate, CardsListFilter, CardUpdate
from std_cards.services.card_service import build_acl_filter


async def _make_user(session_maker, role: UserRole = UserRole.ADMIN):
    repo = UserRepository(session_maker)
    return await repo.create(
        UserCreate(email=f"u{uuid4().hex[:8]}@x.com", password_hash="h", role=role)
    )


def _card_create(category_id: int = 1) -> CardCreate:
    return CardCreate(
        last_name="Тест",
        first_name="Карточка",
        membership_no=f"MBR-{uuid4().hex[:6]}",
        category_id=category_id,
    )


async def test_super_admin_sees_all_cards(session_maker):
    super_admin = await _make_user(session_maker, UserRole.SUPER_ADMIN)
    card_repo = CardRepository(session_maker)
    group_repo = AdminCardGroupRepository(session_maker)

    admin = await _make_user(session_maker, UserRole.ADMIN)
    await card_repo.create(_card_create(category_id=1), slug=f"sa{uuid4().hex[:6]}", created_by=admin.id)
    await card_repo.create(_card_create(category_id=2), slug=f"sb{uuid4().hex[:6]}", created_by=admin.id)
    await card_repo.create(_card_create(category_id=3), slug=f"sc{uuid4().hex[:6]}", created_by=admin.id)

    acl = await build_acl_filter(super_admin, group_repo)
    assert acl is None

    items, total = await card_repo.list(CardsListFilter(), acl_filter=acl)
    assert total == 3


async def test_admin_without_groups_sees_only_assigned(session_maker):
    admin = await _make_user(session_maker, UserRole.ADMIN)
    super_admin = await _make_user(session_maker, UserRole.SUPER_ADMIN)
    card_repo = CardRepository(session_maker)
    group_repo = AdminCardGroupRepository(session_maker)

    own_card = await card_repo.create(
        _card_create(category_id=1),
        slug=f"own{uuid4().hex[:6]}",
        created_by=admin.id,
    )
    await card_repo.update(own_card.id, CardUpdate(assigned_admin_id=admin.id))

    other_card = await card_repo.create(
        _card_create(category_id=2),
        slug=f"oth{uuid4().hex[:6]}",
        created_by=super_admin.id,
    )

    acl = await build_acl_filter(admin, group_repo)
    assert acl is not None

    items, total = await card_repo.list(CardsListFilter(), acl_filter=acl)
    ids = {i.id for i in items}
    assert own_card.id in ids
    assert other_card.id not in ids


async def test_admin_with_group_sees_category_cards(session_maker):
    admin = await _make_user(session_maker, UserRole.ADMIN)
    super_admin = await _make_user(session_maker, UserRole.SUPER_ADMIN)
    card_repo = CardRepository(session_maker)
    group_repo = AdminCardGroupRepository(session_maker)

    await group_repo.set_groups(admin.id, [1], can_export=False)

    platinum_card = await card_repo.create(
        _card_create(category_id=1),
        slug=f"plat{uuid4().hex[:6]}",
        created_by=super_admin.id,
    )
    gold_card = await card_repo.create(
        _card_create(category_id=2),
        slug=f"gold{uuid4().hex[:6]}",
        created_by=super_admin.id,
    )

    acl = await build_acl_filter(admin, group_repo)
    items, total = await card_repo.list(CardsListFilter(), acl_filter=acl)
    ids = {i.id for i in items}
    assert platinum_card.id in ids
    assert gold_card.id not in ids


async def test_acl_miss_returns_none_not_403(session_maker):
    admin = await _make_user(session_maker, UserRole.ADMIN)
    super_admin = await _make_user(session_maker, UserRole.SUPER_ADMIN)
    card_repo = CardRepository(session_maker)
    group_repo = AdminCardGroupRepository(session_maker)

    await group_repo.set_groups(admin.id, [1], can_export=False)

    gold_card = await card_repo.create(
        _card_create(category_id=2),
        slug=f"miss{uuid4().hex[:6]}",
        created_by=super_admin.id,
    )

    acl = await build_acl_filter(admin, group_repo)
    result = await card_repo.get_by_id(gold_card.id, acl_filter=acl)
    assert result is None


async def test_assigned_gives_access_regardless_of_groups(session_maker):
    admin = await _make_user(session_maker, UserRole.ADMIN)
    super_admin = await _make_user(session_maker, UserRole.SUPER_ADMIN)
    card_repo = CardRepository(session_maker)
    group_repo = AdminCardGroupRepository(session_maker)

    assigned_card = await card_repo.create(
        _card_create(category_id=3),
        slug=f"asgn{uuid4().hex[:6]}",
        created_by=super_admin.id,
    )
    await card_repo.update(assigned_card.id, CardUpdate(assigned_admin_id=admin.id))

    acl = await build_acl_filter(admin, group_repo)
    result = await card_repo.get_by_id(assigned_card.id, acl_filter=acl)
    assert result is not None
    assert result.id == assigned_card.id
