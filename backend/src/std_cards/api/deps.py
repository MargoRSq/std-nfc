from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.core.exceptions import ForbiddenError, UnauthorizedError
from std_cards.core.nats.publisher import NatsPublisher
from std_cards.db.session import SessionMaker, get_session_maker
from std_cards.infrastructure.minio import MinioClient, get_minio
from std_cards.infrastructure.repositories import (
    AdminCardGroupRepository,
    AuditRepository,
    CardMessageRepository,
    CardRepository,
    CategoryRepository,
    FeedbackRepository,
    ImportJobRepository,
    LabelPresetRepository,
    LoginChallengeRepository,
    PasswordResetRepository,
    RefreshTokenRepository,
    TemplateRepository,
    UserRepository,
)
from std_cards.models.auth import UserDB, UserRole
from std_cards.services.admin_service import AdminService
from std_cards.services.auth_service import AuthService
from std_cards.services.card_message_service import CardMessageService
from std_cards.services.card_service import CardService
from std_cards.services.import_service import ImportService
from std_cards.services.media_service import MediaService
from std_cards.services.slug_service import SlugService
from std_cards.services.template_service import TemplateService

bearer_scheme = HTTPBearer(auto_error=False)


def db_session_maker() -> SessionMaker:
    return get_session_maker()


async def db_connection(
    sm: SessionMaker = Depends(db_session_maker),
) -> AsyncIterator[AsyncConnection]:
    async with sm.session() as conn:
        yield conn


def get_user_repo(sm: SessionMaker = Depends(db_session_maker)) -> UserRepository:
    return UserRepository(sm)


def get_refresh_repo(sm: SessionMaker = Depends(db_session_maker)) -> RefreshTokenRepository:
    return RefreshTokenRepository(sm)


def get_challenge_repo(sm: SessionMaker = Depends(db_session_maker)) -> LoginChallengeRepository:
    return LoginChallengeRepository(sm)


def get_password_reset_repo(
    sm: SessionMaker = Depends(db_session_maker),
) -> PasswordResetRepository:
    return PasswordResetRepository(sm)


def get_audit_repo(sm: SessionMaker = Depends(db_session_maker)) -> AuditRepository:
    return AuditRepository(sm)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    refresh_repo: RefreshTokenRepository = Depends(get_refresh_repo),
    challenge_repo: LoginChallengeRepository = Depends(get_challenge_repo),
    password_reset_repo: PasswordResetRepository = Depends(get_password_reset_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
) -> AuthService:
    return AuthService(user_repo, refresh_repo, challenge_repo, password_reset_repo, audit_repo)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> UserDB:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError(message="Authorization Bearer required")
    return await auth.get_current_user(credentials.credentials)


async def require_admin(user: UserDB = Depends(get_current_user)) -> UserDB:
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise ForbiddenError()
    return user


async def require_super_admin(user: UserDB = Depends(get_current_user)) -> UserDB:
    if user.role != UserRole.SUPER_ADMIN:
        raise ForbiddenError()
    return user


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDep = Annotated[UserDB, Depends(get_current_user)]
AdminDep = Annotated[UserDB, Depends(require_admin)]
SuperAdminDep = Annotated[UserDB, Depends(require_super_admin)]


def get_card_repo(sm: SessionMaker = Depends(db_session_maker)) -> CardRepository:
    return CardRepository(sm)


def get_category_repo(sm: SessionMaker = Depends(db_session_maker)) -> CategoryRepository:
    return CategoryRepository(sm)


def get_slug_service(card_repo: CardRepository = Depends(get_card_repo)) -> SlugService:
    return SlugService(card_repo)


def get_admin_card_group_repo(
    sm: SessionMaker = Depends(db_session_maker),
) -> AdminCardGroupRepository:
    return AdminCardGroupRepository(sm)


def get_card_service(
    card_repo: CardRepository = Depends(get_card_repo),
    slug_service: SlugService = Depends(get_slug_service),
    category_repo: CategoryRepository = Depends(get_category_repo),
    group_repo: AdminCardGroupRepository = Depends(get_admin_card_group_repo),
    template_repo: TemplateRepository = Depends(
        lambda sm=Depends(db_session_maker): TemplateRepository(sm)
    ),
) -> CardService:
    return CardService(card_repo, slug_service, category_repo, group_repo, template_repo)


def get_admin_service(
    user_repo: UserRepository = Depends(get_user_repo),
    group_repo: AdminCardGroupRepository = Depends(get_admin_card_group_repo),
    refresh_repo: RefreshTokenRepository = Depends(get_refresh_repo),
    audit_repo: AuditRepository = Depends(get_audit_repo),
    category_repo: CategoryRepository = Depends(get_category_repo),
) -> AdminService:
    return AdminService(user_repo, group_repo, refresh_repo, audit_repo, category_repo)


CardServiceDep = Annotated[CardService, Depends(get_card_service)]
CategoryRepoDep = Annotated[CategoryRepository, Depends(get_category_repo)]
AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
AuditRepoDep = Annotated[AuditRepository, Depends(get_audit_repo)]


def get_nats_publisher(request: Request) -> NatsPublisher | None:
    return getattr(request.app.state, "nats_publisher", None)


def get_template_repo(sm: SessionMaker = Depends(db_session_maker)) -> TemplateRepository:
    return TemplateRepository(sm)


def get_import_job_repo(sm: SessionMaker = Depends(db_session_maker)) -> ImportJobRepository:
    return ImportJobRepository(sm)


def get_minio_client() -> MinioClient:
    return get_minio()


def get_template_service(
    template_repo: TemplateRepository = Depends(get_template_repo),
    card_repo: CardRepository = Depends(get_card_repo),
    category_repo: CategoryRepository = Depends(get_category_repo),
) -> TemplateService:
    return TemplateService(template_repo, card_repo, category_repo)


def get_import_service(
    import_repo: ImportJobRepository = Depends(get_import_job_repo),
    card_repo: CardRepository = Depends(get_card_repo),
    template_repo: TemplateRepository = Depends(get_template_repo),
    minio: MinioClient = Depends(get_minio_client),
    nats_publisher: NatsPublisher | None = Depends(get_nats_publisher),
) -> ImportService:
    return ImportService(import_repo, card_repo, template_repo, minio, nats_publisher)


TemplateServiceDep = Annotated[TemplateService, Depends(get_template_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]


def get_media_service(
    minio: MinioClient = Depends(get_minio_client),
    card_repo: CardRepository = Depends(get_card_repo),
) -> MediaService:
    return MediaService(minio, card_repo)


MediaServiceDep = Annotated[MediaService, Depends(get_media_service)]


def get_scan_repo(sm: SessionMaker = Depends(db_session_maker)) -> "ScanEventRepository":
    from std_cards.infrastructure.repositories.scan_repo import ScanEventRepository

    return ScanEventRepository(sm)


def get_scan_service(
    nats_publisher: NatsPublisher | None = Depends(get_nats_publisher),
) -> "ScanService":
    from std_cards.services.scan_service import ScanService

    return ScanService(nats_publisher)


def get_analytics_service(
    scan_repo: "ScanEventRepository" = Depends(get_scan_repo),
    card_repo: CardRepository = Depends(get_card_repo),
    group_repo: AdminCardGroupRepository = Depends(get_admin_card_group_repo),
) -> "AnalyticsService":
    from std_cards.services.analytics_service import AnalyticsService

    return AnalyticsService(scan_repo, card_repo, group_repo)


from std_cards.infrastructure.repositories.scan_repo import ScanEventRepository  # noqa: E402
from std_cards.services.analytics_service import AnalyticsService  # noqa: E402
from std_cards.services.scan_service import ScanService  # noqa: E402

ScanRepoDep = Annotated[ScanEventRepository, Depends(get_scan_repo)]
ScanServiceDep = Annotated[ScanService, Depends(get_scan_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


def get_feedback_repo(sm: SessionMaker = Depends(db_session_maker)) -> FeedbackRepository:
    return FeedbackRepository(sm)


FeedbackRepoDep = Annotated[FeedbackRepository, Depends(get_feedback_repo)]


def get_card_message_repo(
    sm: SessionMaker = Depends(db_session_maker),
) -> CardMessageRepository:
    return CardMessageRepository(sm)


def get_card_message_service(
    message_repo: CardMessageRepository = Depends(get_card_message_repo),
    card_repo: CardRepository = Depends(get_card_repo),
    minio: MinioClient = Depends(get_minio_client),
) -> CardMessageService:
    return CardMessageService(message_repo, card_repo, minio)


CardMessageRepoDep = Annotated[CardMessageRepository, Depends(get_card_message_repo)]
CardMessageServiceDep = Annotated[CardMessageService, Depends(get_card_message_service)]


def get_label_preset_repo(
    sm: SessionMaker = Depends(db_session_maker),
) -> LabelPresetRepository:
    return LabelPresetRepository(sm)


LabelPresetRepoDep = Annotated[LabelPresetRepository, Depends(get_label_preset_repo)]
