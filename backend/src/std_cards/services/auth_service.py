import contextlib
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from std_cards.config import settings
from std_cards.core.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidCredentialsError,
    NotFoundError,
    RateLimitedError,
    RefreshReuseError,
    UnauthorizedError,
)
from std_cards.core.mailer import send_password_reset
from std_cards.core.ratelimit import login_rate_limiter
from std_cards.core.security import (
    create_access_token,
    decode_access_token,
    generate_recovery_codes,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from std_cards.core.totp import (
    generate_totp_secret,
    provisioning_uri,
    qr_code_png_base64,
    verify_totp_step,
)
from std_cards.infrastructure.repositories import (
    AuditRepository,
    LoginChallengeRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
    UserRepository,
)
from std_cards.models.audit import AuditAction
from std_cards.models.auth import ConsumeResult, UserDB, UserPublic

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_repo: RefreshTokenRepository,
        challenge_repo: LoginChallengeRepository,
        password_reset_repo: PasswordResetRepository,
        audit_repo: AuditRepository | None = None,
    ) -> None:
        self.users = user_repo
        self.refresh = refresh_repo
        self.challenges = challenge_repo
        self.password_resets = password_reset_repo
        self.audit = audit_repo

    async def _audit(
        self,
        action: AuditAction,
        *,
        actor_id: UUID | None = None,
        actor_email: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        diff: dict | None = None,
    ) -> None:
        if self.audit is None:
            return
        with contextlib.suppress(Exception):
            await self.audit.write(
                actor_id=actor_id,
                actor_email=actor_email,
                action=action.value,
                ip=ip,
                user_agent=user_agent,
                diff=diff,
            )

    async def login_step1(
        self,
        email: str,
        password: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Phase 1 login: валидирует email+password, применяет rate limit и account lockout.

        Если у пользователя включён TOTP — возвращает challenge_token вместо токенов,
        чтобы требовать прохождения Phase 2. Так мы не выдаём сессию до полной 2FA.
        """
        if ip and not await login_rate_limiter.check(
            scope="login_ip",
            identifier=ip,
            limit=settings.RATE_LIMIT.LOGIN_IP_PER_MIN,
            window_seconds=60,
        ):
            await self._audit(
                AuditAction.LOGIN_FAIL,
                actor_email=email,
                ip=ip,
                user_agent=user_agent,
                diff={"reason": "rate_limited_ip"},
            )
            raise RateLimitedError(message="Too many login attempts, try later")

        ok = await login_rate_limiter.check(
            scope="login",
            identifier=email.lower(),
            limit=settings.RATE_LIMIT.LOGIN_PER_MIN,
            window_seconds=60,
        )
        if not ok:
            await self._audit(
                AuditAction.LOGIN_FAIL,
                actor_email=email,
                ip=ip,
                user_agent=user_agent,
                diff={"reason": "rate_limited"},
            )
            raise RateLimitedError(message="Too many login attempts, try later")

        user = await self.users.get_by_email(email)
        if user is None:
            await self._audit(
                AuditAction.LOGIN_FAIL,
                actor_email=email,
                ip=ip,
                user_agent=user_agent,
                diff={"reason": "user_not_found"},
            )
            raise InvalidCredentialsError()
        if not user.is_active:
            await self._audit(
                AuditAction.LOGIN_FAIL,
                actor_id=user.id,
                actor_email=user.email,
                ip=ip,
                user_agent=user_agent,
                diff={"reason": "inactive"},
            )
            raise ForbiddenError(message="Учётная запись отключена")
        if await self.users.is_locked(user.id):
            await self._audit(
                AuditAction.LOGIN_FAIL,
                actor_id=user.id,
                actor_email=user.email,
                ip=ip,
                user_agent=user_agent,
                diff={"reason": "locked"},
            )
            raise UnauthorizedError(message="Учётная запись временно заблокирована")

        if not verify_password(password, user.password_hash):
            await self.users.increment_failed_login(user.id)
            await self._audit(
                AuditAction.LOGIN_FAIL,
                actor_id=user.id,
                actor_email=user.email,
                ip=ip,
                user_agent=user_agent,
                diff={"reason": "invalid_password"},
            )
            raise InvalidCredentialsError()

        if user.totp_enabled:
            return await self._issue_challenge(user.id, ip)

        await self.users.reset_failed_login(user.id)
        tokens = await self._issue_tokens(user, ip=ip, user_agent=user_agent)
        await self._audit(
            AuditAction.LOGIN_SUCCESS,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
            diff={"method": "password"},
        )
        return tokens

    async def _issue_challenge(self, user_id: UUID, ip: str | None) -> dict:
        """Создаёт одноразовый challenge для TOTP Phase 2.

        Токен хранится в БД в виде SHA-256 хеша — в случае компрометации БД
        сырой токен остаётся неизвестным атакующему.
        """
        raw = secrets.token_urlsafe(32)
        challenge_hash = hashlib.sha256(raw.encode()).hexdigest()
        await self.challenges.create(
            user_id=user_id,
            challenge_hash=challenge_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            ip=ip,
        )
        return {"stage": "totp_required", "challenge_token": raw}

    async def login_step2_totp(
        self,
        challenge_token: str,
        code: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Phase 2: проверяет TOTP-код по ранее выданному challenge.

        Challenge одноразовый — после consume повторная попытка с тем же токеном отклоняется.
        """
        challenge_hash = hashlib.sha256(challenge_token.encode()).hexdigest()
        challenge = await self.challenges.get_by_hash(challenge_hash)
        if challenge is None:
            raise UnauthorizedError(message="Challenge token invalid or expired")
        if challenge.consumed_at is not None or challenge.expires_at <= datetime.now(UTC):
            raise UnauthorizedError(message="Challenge already used or expired")

        user = await self.users.get_by_id(challenge.user_id)
        if user is None or not user.is_active or user.totp_secret is None:
            raise UnauthorizedError(message="Invalid state")
        if await self.users.is_locked(user.id):
            raise UnauthorizedError(message="Учётная запись временно заблокирована")
        if not await login_rate_limiter.check(
            scope="totp",
            identifier=str(user.id),
            limit=settings.RATE_LIMIT.LOGIN_PER_MIN,
            window_seconds=60,
        ):
            raise RateLimitedError(message="Too many code attempts, try later")

        matched_step = verify_totp_step(user.totp_secret, code, after_step=user.last_totp_step)
        if matched_step is None or not await self.users.advance_totp_step(user.id, matched_step):
            await self.users.increment_failed_login(user.id)
            await self._audit(
                AuditAction.TOTP_FAIL,
                actor_id=user.id,
                actor_email=user.email,
                ip=ip,
                user_agent=user_agent,
            )
            raise UnauthorizedError(message="Неверный код")

        result = await self.challenges.consume(challenge.id)
        if result != ConsumeResult.CONSUMED:
            raise UnauthorizedError(message="Challenge already used or expired")

        await self.users.reset_failed_login(user.id)
        tokens = await self._issue_tokens(user, ip=ip, user_agent=user_agent)
        await self._audit(
            AuditAction.TOTP_VERIFY,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
        )
        await self._audit(
            AuditAction.LOGIN_SUCCESS,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
            diff={"method": "totp"},
        )
        return tokens

    async def login_step2_recovery(
        self,
        challenge_token: str,
        recovery_code: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Phase 2 альтернатива: вход через одноразовый recovery code вместо TOTP.

        Recovery codes хранятся как bcrypt-хеши, поэтому перебираем verify_password
        по каждому. После использования код атомарно удаляется из массива.
        """
        challenge_hash = hashlib.sha256(challenge_token.encode()).hexdigest()
        challenge = await self.challenges.get_by_hash(challenge_hash)
        if (
            challenge is None
            or challenge.consumed_at is not None
            or challenge.expires_at <= datetime.now(UTC)
        ):
            raise UnauthorizedError(message="Challenge token invalid or expired")

        user = await self.users.get_by_id(challenge.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(message="Invalid state")
        if await self.users.is_locked(user.id):
            raise UnauthorizedError(message="Учётная запись временно заблокирована")
        if not await login_rate_limiter.check(
            scope="recovery",
            identifier=str(user.id),
            limit=settings.RATE_LIMIT.LOGIN_PER_MIN,
            window_seconds=60,
        ):
            raise RateLimitedError(message="Too many code attempts, try later")

        if user.recovery_codes is None:
            raise UnauthorizedError(message="No recovery codes available")

        matched_hash = None
        for stored_hash in user.recovery_codes:
            if verify_password(recovery_code, stored_hash):
                matched_hash = stored_hash
                break
        if matched_hash is None:
            await self.users.increment_failed_login(user.id)
            await self._audit(
                AuditAction.TOTP_FAIL,
                actor_id=user.id,
                actor_email=user.email,
                ip=ip,
                user_agent=user_agent,
                diff={"method": "recovery"},
            )
            raise UnauthorizedError(message="Неверный код восстановления")

        consumed = await self.users.consume_recovery_code(user.id, matched_hash)
        if not consumed:
            raise UnauthorizedError(message="Неверный код восстановления")

        await self.challenges.consume(challenge.id)
        await self.users.reset_failed_login(user.id)
        tokens = await self._issue_tokens(user, ip=ip, user_agent=user_agent)
        await self._audit(
            AuditAction.RECOVERY_USE,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
        )
        await self._audit(
            AuditAction.LOGIN_SUCCESS,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
            diff={"method": "recovery"},
        )
        return tokens

    async def _issue_tokens(
        self,
        user: UserDB,
        *,
        ip: str | None,
        user_agent: str | None,
        family_id: UUID | None = None,
    ) -> dict:
        """Выпускает access+refresh пару для подтверждённого пользователя.

        family_id=None означает новый login — repo.create сгенерирует новый uuid4.
        При refresh rotation family_id прокидывается явно, чтобы вся цепочка была revocable.
        """
        access = create_access_token(
            user_id=user.id, role=user.role, token_version=user.token_version
        )
        pair = generate_refresh_token()
        await self.refresh.create(
            user_id=user.id,
            token_hash=pair.hashed,
            expires_at=datetime.now(UTC) + timedelta(days=settings.AUTH.REFRESH_EXPIRE_DAYS),
            family_id=family_id,
            user_agent=user_agent,
            ip=ip,
        )
        return {
            "stage": "completed",
            "access_token": access,
            "refresh_token": pair.raw,
            "user": UserPublic.model_validate(user, from_attributes=True).model_dump(mode="json"),
        }

    async def refresh_tokens(
        self,
        refresh_token_raw: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Refresh rotation с reuse-detection.

        Если токен уже revoked — кто-то использует старый токен (утечка или кража).
        В этом случае revoke'им всю family — и атакующий, и легитимный пользователь
        теряют сессию, что форсирует повторный полный login.
        """
        token_hash = hash_refresh_token(refresh_token_raw)
        existing = await self.refresh.get_by_hash(token_hash)
        if existing is None:
            raise UnauthorizedError(message="Invalid refresh token")

        if existing.revoked_at is not None:
            await self.refresh.revoke_chain_from(existing.id)
            raise RefreshReuseError()

        if existing.expires_at <= datetime.now(UTC):
            raise UnauthorizedError(message="Refresh token expired")

        user = await self.users.get_by_id(existing.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(message="Invalid state")

        pair = generate_refresh_token()
        new_db = await self.refresh.create(
            user_id=user.id,
            token_hash=pair.hashed,
            expires_at=datetime.now(UTC) + timedelta(days=settings.AUTH.REFRESH_EXPIRE_DAYS),
            family_id=existing.family_id,
            user_agent=user_agent,
            ip=ip,
        )
        await self.refresh.revoke(existing.id, replaced_by_id=new_db.id)

        access = create_access_token(
            user_id=user.id, role=user.role, token_version=user.token_version
        )
        return {
            "access_token": access,
            "refresh_token": pair.raw,
            "user": UserPublic.model_validate(user, from_attributes=True).model_dump(mode="json"),
        }

    async def logout(
        self,
        refresh_token_raw: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Отзывает всю token family по предъявленному refresh token.

        Revoke всей family (а не только конкретного токена) гарантирует,
        что параллельные вкладки/устройства одной family тоже теряют сессию.
        """
        token_hash = hash_refresh_token(refresh_token_raw)
        existing = await self.refresh.get_by_hash(token_hash)
        if existing is None or existing.revoked_at is not None:
            return
        user_id = existing.user_id
        await self.refresh.revoke_chain_from(existing.id)
        user = await self.users.get_by_id(user_id)
        await self._audit(
            AuditAction.LOGOUT,
            actor_id=user_id,
            actor_email=user.email if user else None,
            ip=ip,
            user_agent=user_agent,
        )

    async def force_logout_all(self, user_id: UUID) -> None:
        """Bump token_version + revoke всех refresh — инвалидирует все выданные access и refresh токены.

        Используется при смене пароля, подозрительной активности или явном "выйти со всех устройств".
        token_version в JWT payload проверяется при каждом запросе — bump делает старые access токены
        невалидными даже до их истечения.
        """
        async with self.users.session_maker.session() as conn:
            await self.users.bump_token_version(user_id, conn=conn)
            await self.refresh.revoke_all_for_user(user_id, conn=conn)

    async def totp_enroll(self, user_id: UUID) -> dict:
        """Начинает процесс включения TOTP: генерирует секрет, сохраняет как pending (enabled=False).

        Секрет сохраняется сразу, чтобы пользователь мог добавить аккаунт в authenticator
        и затем подтвердить через totp_verify. До verify TOTP не применяется при логине.
        """
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        if user.totp_enabled:
            raise ConflictError(message="TOTP already enabled")
        secret = generate_totp_secret()
        await self.users.set_totp(user.id, secret=secret, enabled=False, recovery_codes=None)
        uri = provisioning_uri(secret, email=user.email, issuer=settings.AUTH.TOTP_ISSUER)
        qr_b64 = qr_code_png_base64(uri)
        return {"otpauth_url": uri, "qr_png_base64": qr_b64}

    async def totp_verify(
        self,
        user_id: UUID,
        code: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Подтверждает enrollment: проверяет код, активирует TOTP, генерирует recovery codes.

        Recovery codes возвращаются только один раз — при activate. Потом они доступны только
        как bcrypt-хеши в БД, plain-коды нигде не хранятся.
        """
        user = await self.users.get_by_id(user_id)
        if user is None or user.totp_secret is None:
            raise ConflictError(message="TOTP not enrolled — call totp_enroll first")
        if user.totp_enabled:
            raise ConflictError(message="TOTP already enabled")
        matched_step = verify_totp_step(user.totp_secret, code)
        if matched_step is None:
            raise UnauthorizedError(message="Неверный код")

        plain_codes = generate_recovery_codes(n=10)
        bcrypt_hashes = [hash_password(c) for c in plain_codes]
        await self.users.set_totp(
            user.id, secret=user.totp_secret, enabled=True, recovery_codes=bcrypt_hashes
        )
        await self.users.set_last_totp_step(user.id, matched_step)
        await self._audit(
            AuditAction.TOTP_ENROLL,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
        )
        return {"recovery_codes": plain_codes}

    async def totp_disable(
        self,
        user_id: UUID,
        password: str,
        code: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Отключает TOTP: требует подтверждения паролем + текущим TOTP-кодом.

        Двойная проверка (password + TOTP) защищает от сценария, где атакующий
        имеет только сессию пользователя, но не знает пароль.
        """
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError(message="Неверный пароль")
        if not user.totp_enabled or user.totp_secret is None:
            raise ConflictError(message="TOTP not enabled")
        if verify_totp_step(user.totp_secret, code, after_step=user.last_totp_step) is None:
            raise UnauthorizedError(message="Неверный код")
        await self.users.set_totp(user.id, secret=None, enabled=False, recovery_codes=None)
        await self._audit(
            AuditAction.TOTP_DISABLE,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
        )

    async def password_reset_request(
        self,
        email: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> str | None:
        """Создаёт reset-токен для email. Не раскрывает факт существования аккаунта.

        В prod этот метод должен публиковать задачу в NATS и возвращать None.
        Сейчас возвращает raw токен для integration-тестирования без email-сервиса.
        """
        user = await self.users.get_by_email(email)
        if user is None:
            await self._audit(
                AuditAction.PASSWORD_RESET_REQUEST,
                actor_email=email,
                ip=ip,
                user_agent=user_agent,
                diff={"result": "user_not_found"},
            )
            return None
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        await self.password_resets.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
        await self._audit(
            AuditAction.PASSWORD_RESET_REQUEST,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
        )
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw}"
        try:
            await send_password_reset(user.email, reset_url)
        except Exception:
            # Письмо не ушло — токен всё равно создан, юзер может повторить запрос.
            # Ошибку наружу не отдаём: 204 не должен раскрывать существование аккаунта.
            logger.exception("Не удалось отправить письмо сброса пароля на %s", user.email)
        return raw

    async def password_reset_confirm(
        self,
        token: str,
        new_password: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Применяет новый пароль по reset-токену, затем инвалидирует все сессии.

        После смены пароля форсируем полный logout: bump token_version + revoke all refresh.
        Это защищает от сценария, где атакующий сменил пароль, но старый владелец ещё активен.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset = await self.password_resets.get_by_hash(token_hash)
        if reset is None:
            raise UnauthorizedError(message="Invalid or expired reset token")
        if reset.consumed_at is not None or reset.expires_at <= datetime.now(UTC):
            raise UnauthorizedError(message="Invalid or expired reset token")
        async with self.users.session_maker.session() as conn:
            result = await self.password_resets.consume(reset.id, conn=conn)
            if result != ConsumeResult.CONSUMED:
                raise UnauthorizedError(message="Invalid or expired reset token")
            await self.users.update_password(reset.user_id, hash_password(new_password), conn=conn)
            await self.users.bump_token_version(reset.user_id, conn=conn)
            await self.refresh.revoke_all_for_user(reset.user_id, conn=conn)
        user = await self.users.get_by_id(reset.user_id)
        await self._audit(
            AuditAction.PASSWORD_RESET_CONFIRM,
            actor_id=reset.user_id,
            actor_email=user.email if user else None,
            ip=ip,
            user_agent=user_agent,
        )

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError(message="Неверный текущий пароль")
        async with self.users.session_maker.session() as conn:
            await self.users.update_password(user_id, hash_password(new_password), conn=conn)
            await self.users.bump_token_version(user_id, conn=conn)
            await self.refresh.revoke_all_for_user(user_id, conn=conn)
        await self._audit(
            AuditAction.PASSWORD_CHANGE,
            actor_id=user.id,
            actor_email=user.email,
            ip=ip,
            user_agent=user_agent,
        )

    async def get_current_user(self, access_token: str) -> UserDB:
        """Декодирует access token, проверяет token_version для защиты от отозванных сессий.

        token_version в JWT должен совпадать с версией в БД — иначе токен выдан до
        force_logout_all или смены пароля и должен быть отклонён.
        """
        try:
            claims = decode_access_token(access_token)
        except UnauthorizedError:
            raise
        user_id = UUID(claims["sub"])
        token_version = claims.get("tv")
        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(message="User not found or inactive")
        if user.token_version != token_version:
            raise UnauthorizedError(message="Token version mismatch — please re-login")
        return user
