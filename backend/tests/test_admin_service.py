from uuid import uuid4

import pytest

from std_cards.core.security import hash_password, verify_password
from std_cards.infrastructure.repositories.admin_card_groups_repo import AdminCardGroupRepository
from std_cards.infrastructure.repositories.audit_repo import AuditRepository
from std_cards.infrastructure.repositories.category_repo import CategoryRepository
from std_cards.infrastructure.repositories.refresh_token_repo import RefreshTokenRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.admin import AdminInvite
from std_cards.models.auth import UserCreate, UserRole
from std_cards.services.admin_service import AdminService


def _make_service(session_maker) -> AdminService:
    return AdminService(
        user_repo=UserRepository(session_maker),
        group_repo=AdminCardGroupRepository(session_maker),
        refresh_repo=RefreshTokenRepository(session_maker),
        audit_repo=AuditRepository(session_maker),
        category_repo=CategoryRepository(session_maker),
    )


async def _make_super_admin(session_maker):
    repo = UserRepository(session_maker)
    return await repo.create(
        UserCreate(
            email=f"sa{uuid4().hex[:6]}@x.com",
            password_hash=hash_password("password"),
            role=UserRole.SUPER_ADMIN,
        )
    )


async def test_create_admin_returns_user_and_temp_password(session_maker):
    actor = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)

    invite = AdminInvite(email=f"admin{uuid4().hex[:6]}@x.com", category_ids=[1, 2])
    user, temp_pw = await svc.create_admin(invite, actor=actor)

    assert user.email == invite.email
    assert user.role == UserRole.ADMIN
    assert len(temp_pw) >= 12

    audit_repo = AuditRepository(session_maker)
    entries, total = await audit_repo.list_with_filters(entity_id=str(user.id))
    assert total >= 1
    assert entries[0].action == "admin.create"


async def test_create_admin_sets_groups(session_maker):
    actor = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)
    group_repo = AdminCardGroupRepository(session_maker)

    invite = AdminInvite(email=f"adm{uuid4().hex[:6]}@x.com", category_ids=[1, 2], can_export=True)
    user, _ = await svc.create_admin(invite, actor=actor)

    cats = await group_repo.categories_for_user(user.id)
    assert set(cats) == {1, 2}


async def test_create_admin_duplicate_email_raises_conflict(session_maker):
    from std_cards.core.exceptions import ConflictError

    actor = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)

    invite = AdminInvite(email=f"dup{uuid4().hex[:6]}@x.com")
    await svc.create_admin(invite, actor=actor)

    with pytest.raises(ConflictError):
        await svc.create_admin(invite, actor=actor)


async def test_reset_password_invalidates_old_version(session_maker):
    actor = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)
    user_repo = UserRepository(session_maker)

    invite = AdminInvite(email=f"rp{uuid4().hex[:6]}@x.com")
    target, old_pw = await svc.create_admin(invite, actor=actor)

    old_version = (await user_repo.get_by_id(target.id)).token_version

    new_pw = await svc.reset_password(target.id, actor=actor)
    assert new_pw != old_pw

    updated = await user_repo.get_by_id(target.id)
    assert updated.token_version > old_version
    assert verify_password(new_pw, updated.password_hash)


async def test_force_logout_bumps_token_version(session_maker):
    actor = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)
    user_repo = UserRepository(session_maker)

    invite = AdminInvite(email=f"fl{uuid4().hex[:6]}@x.com")
    target, _ = await svc.create_admin(invite, actor=actor)
    old_version = (await user_repo.get_by_id(target.id)).token_version

    await svc.force_logout(target.id, actor=actor)

    updated = await user_repo.get_by_id(target.id)
    assert updated.token_version > old_version


async def test_delete_admin_deactivates(session_maker):
    actor = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)
    user_repo = UserRepository(session_maker)

    invite = AdminInvite(email=f"del{uuid4().hex[:6]}@x.com")
    target, _ = await svc.create_admin(invite, actor=actor)

    await svc.delete_admin(target.id, actor=actor)

    updated = await user_repo.get_by_id(target.id)
    assert updated.is_active is False


async def test_cannot_deactivate_self_even_with_other_supers(session_maker):
    from std_cards.core.exceptions import ForbiddenError
    from std_cards.models.admin import AdminUpdate

    actor = await _make_super_admin(session_maker)
    await _make_super_admin(session_maker)  # другой активный супер-админ
    svc = _make_service(session_maker)
    user_repo = UserRepository(session_maker)

    with pytest.raises(ForbiddenError):
        await svc.update_admin(actor.id, AdminUpdate(is_active=False), actor=actor)

    assert (await user_repo.get_by_id(actor.id)).is_active is True


async def test_cannot_demote_self_even_with_other_supers(session_maker):
    from std_cards.core.exceptions import ForbiddenError
    from std_cards.models.admin import AdminUpdate

    actor = await _make_super_admin(session_maker)
    await _make_super_admin(session_maker)
    svc = _make_service(session_maker)
    user_repo = UserRepository(session_maker)

    with pytest.raises(ForbiddenError):
        await svc.update_admin(actor.id, AdminUpdate(role=UserRole.ADMIN), actor=actor)

    assert (await user_repo.get_by_id(actor.id)).role == UserRole.SUPER_ADMIN


async def test_cannot_delete_self_even_with_other_supers(session_maker):
    from std_cards.core.exceptions import ForbiddenError

    actor = await _make_super_admin(session_maker)
    await _make_super_admin(session_maker)
    svc = _make_service(session_maker)
    user_repo = UserRepository(session_maker)

    with pytest.raises(ForbiddenError):
        await svc.delete_admin(actor.id, actor=actor)

    assert (await user_repo.get_by_id(actor.id)).is_active is True


async def test_can_deactivate_other_super_admin(session_maker):
    from std_cards.models.admin import AdminUpdate

    actor = await _make_super_admin(session_maker)
    other = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)
    user_repo = UserRepository(session_maker)

    await svc.update_admin(other.id, AdminUpdate(is_active=False), actor=actor)

    assert (await user_repo.get_by_id(other.id)).is_active is False


async def test_list_admins_returns_all(session_maker):
    actor = await _make_super_admin(session_maker)
    svc = _make_service(session_maker)

    invite1 = AdminInvite(email=f"ls1{uuid4().hex[:6]}@x.com", category_ids=[1])
    invite2 = AdminInvite(email=f"ls2{uuid4().hex[:6]}@x.com", category_ids=[2])
    await svc.create_admin(invite1, actor=actor)
    await svc.create_admin(invite2, actor=actor)

    all_admins = await svc.list_admins()
    emails = {a.email for a in all_admins}
    assert invite1.email in emails
    assert invite2.email in emails
