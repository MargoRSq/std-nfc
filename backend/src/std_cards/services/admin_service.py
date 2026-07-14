import secrets
from uuid import UUID

from std_cards.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from std_cards.core.security import hash_password
from std_cards.infrastructure.repositories.admin_card_groups_repo import AdminCardGroupRepository
from std_cards.infrastructure.repositories.audit_repo import AuditRepository
from std_cards.infrastructure.repositories.category_repo import CategoryRepository
from std_cards.infrastructure.repositories.refresh_token_repo import RefreshTokenRepository
from std_cards.infrastructure.repositories.user_repo import UserRepository
from std_cards.models.admin import AdminInvite, AdminListItem, AdminUpdate
from std_cards.models.audit import AuditAction
from std_cards.models.auth import UserCreate, UserDB, UserRole


class AdminService:
    def __init__(
        self,
        user_repo: UserRepository,
        group_repo: AdminCardGroupRepository,
        refresh_repo: RefreshTokenRepository,
        audit_repo: AuditRepository,
        category_repo: CategoryRepository,
    ) -> None:
        self.users = user_repo
        self.groups = group_repo
        self.refresh = refresh_repo
        self.audit = audit_repo
        self.categories = category_repo

    async def list_admins(self) -> list[AdminListItem]:
        all_users = await self.users.list_by_roles(["admin", "super_admin"])
        items = []
        for user in all_users:
            cats = await self.groups.categories_for_user(user.id)
            items.append(
                AdminListItem(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    role=user.role,
                    is_active=user.is_active,
                    totp_enabled=user.totp_enabled,
                    last_login_at=user.last_login_at,
                    created_at=user.created_at,
                    allowed_categories=cats,
                )
            )
        return items

    async def create_admin(self, data: AdminInvite, actor: UserDB) -> tuple[UserDB, str]:
        existing = await self.users.get_by_email(data.email)
        if existing is not None:
            raise ConflictError(message="Email already taken")

        password = data.initial_password or secrets.token_urlsafe(12)
        user = await self.users.create(
            UserCreate(
                email=data.email,
                name=data.name,
                password_hash=hash_password(password),
                role=data.role,
            )
        )

        if data.role == UserRole.ADMIN and data.category_ids:
            await self.groups.set_groups(user.id, data.category_ids, data.can_export)

        await self.audit.write(
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditAction.ADMIN_CREATE,
            entity_type="user",
            entity_id=str(user.id),
            diff={"role": data.role, "category_ids": data.category_ids},
        )
        return user, password

    async def update_admin(self, admin_id: UUID, data: AdminUpdate, actor: UserDB) -> UserDB:
        user = await self.users.get_by_id(admin_id)
        if user is None:
            raise NotFoundError()

        if actor.id == admin_id:
            if data.is_active is False:
                raise ForbiddenError(
                    message="Нельзя деактивировать собственную учётную запись",
                )
            if data.role is not None and data.role != user.role:
                raise ForbiddenError(
                    message="Нельзя изменить роль собственной учётной записи",
                )

        demoting_self = (
            data.role is not None
            and data.role != UserRole.SUPER_ADMIN
            and user.role == UserRole.SUPER_ADMIN
        )
        deactivating_super = data.is_active is False and user.role == UserRole.SUPER_ADMIN
        if demoting_self or deactivating_super:
            super_admins = await self.users.list_by_roles([UserRole.SUPER_ADMIN.value])
            active_supers = [u for u in super_admins if u.is_active]
            if len(active_supers) <= 1 and active_supers and active_supers[0].id == admin_id:
                raise ConflictError(
                    message="Нельзя понизить или деактивировать последнего супер-админа",
                )

        field_updates: dict = {}
        if data.name is not None:
            field_updates["name"] = data.name
        if data.is_active is not None:
            field_updates["is_active"] = data.is_active
        if data.role is not None:
            field_updates["role"] = data.role

        if field_updates:
            await self.users.update_fields(admin_id, field_updates)

        if data.category_ids is not None:
            effective_role = data.role if data.role is not None else user.role
            if effective_role == UserRole.ADMIN:
                await self.groups.set_groups(
                    admin_id,
                    data.category_ids,
                    data.can_export if data.can_export is not None else False,
                )

        await self.audit.write(
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditAction.ADMIN_UPDATE,
            entity_type="user",
            entity_id=str(admin_id),
            diff=data.model_dump(exclude_unset=True),
        )

        updated = await self.users.get_by_id(admin_id)
        if updated is None:
            raise NotFoundError()
        return updated

    async def delete_admin(self, admin_id: UUID, actor: UserDB) -> None:
        user = await self.users.get_by_id(admin_id)
        if user is None:
            raise NotFoundError()

        if actor.id == admin_id:
            raise ForbiddenError(message="Нельзя удалить собственную учётную запись")

        if user.role == UserRole.SUPER_ADMIN:
            super_admins = await self.users.list_by_roles([UserRole.SUPER_ADMIN.value])
            active_supers = [u for u in super_admins if u.is_active]
            if len(active_supers) <= 1 and active_supers and active_supers[0].id == admin_id:
                raise ConflictError(
                    message="Нельзя удалить последнего супер-админа",
                )

        await self.users.set_active(admin_id, is_active=False)
        await self.users.bump_token_version(admin_id)
        await self.refresh.revoke_all_for_user(admin_id)

        await self.audit.write(
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditAction.ADMIN_DELETE,
            entity_type="user",
            entity_id=str(admin_id),
        )

    async def reset_password(self, admin_id: UUID, actor: UserDB) -> str:
        user = await self.users.get_by_id(admin_id)
        if user is None:
            raise NotFoundError()

        new_pw = secrets.token_urlsafe(12)
        await self.users.update_password(admin_id, hash_password(new_pw))
        await self.users.bump_token_version(admin_id)
        await self.refresh.revoke_all_for_user(admin_id)

        await self.audit.write(
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditAction.ADMIN_RESET_PASSWORD,
            entity_type="user",
            entity_id=str(admin_id),
        )
        return new_pw

    async def reset_2fa(self, admin_id: UUID, actor: UserDB) -> None:
        user = await self.users.get_by_id(admin_id)
        if user is None:
            raise NotFoundError()

        await self.users.set_totp(admin_id, secret=None, enabled=False, recovery_codes=None)
        await self.users.bump_token_version(admin_id)
        await self.refresh.revoke_all_for_user(admin_id)

        await self.audit.write(
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditAction.ADMIN_RESET_2FA,
            entity_type="user",
            entity_id=str(admin_id),
        )

    async def force_logout(self, admin_id: UUID, actor: UserDB) -> None:
        user = await self.users.get_by_id(admin_id)
        if user is None:
            raise NotFoundError()

        await self.users.bump_token_version(admin_id)
        await self.refresh.revoke_all_for_user(admin_id)

        await self.audit.write(
            actor_id=actor.id,
            actor_email=actor.email,
            action=AuditAction.FORCE_LOGOUT,
            entity_type="user",
            entity_id=str(admin_id),
        )
