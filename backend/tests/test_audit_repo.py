from uuid import uuid4

from std_cards.infrastructure.repositories.audit_repo import AuditRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.audit import AuditAction
from std_cards.models.auth import UserCreate, UserRole


async def _make_user(session_maker):
    repo = UserRepository(session_maker)
    return await repo.create(
        UserCreate(email=f"u{uuid4().hex[:8]}@x.com", password_hash="h", role=UserRole.ADMIN)
    )


async def test_write_and_list(session_maker):
    user = await _make_user(session_maker)
    repo = AuditRepository(session_maker)

    await repo.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_CREATE,
        entity_type="card",
        entity_id="some-card-id",
    )

    entries, total = await repo.list_with_filters()
    assert total == 1
    assert entries[0].action == AuditAction.CARD_CREATE
    assert entries[0].entity_type == "card"
    assert entries[0].actor_id == user.id


async def test_write_with_diff(session_maker):
    user = await _make_user(session_maker)
    repo = AuditRepository(session_maker)

    diff = {"before": {"name": "Old"}, "after": {"name": "New"}}
    await repo.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_UPDATE,
        entity_type="card",
        entity_id="card-123",
        diff=diff,
    )

    entries, _ = await repo.list_with_filters(action=AuditAction.CARD_UPDATE)
    assert len(entries) == 1
    assert entries[0].diff == diff


async def test_filter_by_actor_id(session_maker):
    user1 = await _make_user(session_maker)
    user2 = await _make_user(session_maker)
    repo = AuditRepository(session_maker)

    await repo.write(actor_id=user1.id, actor_email=user1.email, action=AuditAction.LOGIN_SUCCESS)
    await repo.write(actor_id=user2.id, actor_email=user2.email, action=AuditAction.LOGIN_FAIL)

    entries, total = await repo.list_with_filters(actor_id=user1.id)
    assert total == 1
    assert entries[0].actor_id == user1.id


async def test_filter_by_action(session_maker):
    user = await _make_user(session_maker)
    repo = AuditRepository(session_maker)

    await repo.write(actor_id=user.id, actor_email=user.email, action=AuditAction.CARD_CREATE)
    await repo.write(actor_id=user.id, actor_email=user.email, action=AuditAction.CARD_DELETE)

    entries, total = await repo.list_with_filters(action=AuditAction.CARD_DELETE)
    assert total == 1
    assert entries[0].action == AuditAction.CARD_DELETE


async def test_filter_by_entity_type(session_maker):
    user = await _make_user(session_maker)
    repo = AuditRepository(session_maker)

    await repo.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.CARD_CREATE,
        entity_type="card",
        entity_id="c1",
    )
    await repo.write(
        actor_id=user.id,
        actor_email=user.email,
        action=AuditAction.ADMIN_CREATE,
        entity_type="user",
        entity_id="u1",
    )

    entries, total = await repo.list_with_filters(entity_type="card")
    assert total == 1
    assert entries[0].entity_type == "card"


async def test_pagination(session_maker):
    user = await _make_user(session_maker)
    repo = AuditRepository(session_maker)

    for _ in range(5):
        await repo.write(
            actor_id=user.id, actor_email=user.email, action=AuditAction.LOGIN_SUCCESS
        )

    entries, total = await repo.list_with_filters(page=1, page_size=2)
    assert total == 5
    assert len(entries) == 2

    entries2, _ = await repo.list_with_filters(page=2, page_size=2)
    assert len(entries2) == 2


async def test_write_anonymous(session_maker):
    repo = AuditRepository(session_maker)

    await repo.write(
        actor_id=None,
        actor_email=None,
        action=AuditAction.LOGIN_FAIL,
        ip="1.2.3.4",
    )

    entries, total = await repo.list_with_filters(action=AuditAction.LOGIN_FAIL)
    assert total == 1
    assert entries[0].actor_id is None
