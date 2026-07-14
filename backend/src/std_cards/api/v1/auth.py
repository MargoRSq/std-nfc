from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from std_cards.api.deps import AuthServiceDep, CurrentUserDep
from std_cards.core.net import client_ip
from std_cards.models.auth import UserPublic

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class LoginTotpRequest(BaseModel):
    challenge_token: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginRecoveryRequest(BaseModel):
    challenge_token: str
    recovery_code: str = Field(min_length=6, max_length=20)


class RefreshRequest(BaseModel):
    refresh_token: str


class TotpVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TotpDisableRequest(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    user: UserPublic


class ChallengeResponse(BaseModel):
    stage: str
    challenge_token: str


class TotpEnrollResponse(BaseModel):
    otpauth_url: str
    qr_png_base64: str


class RecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = client_ip(request)
    ua = request.headers.get("user-agent")
    return ip, ua


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    request: Request,
    auth: AuthServiceDep,
) -> ChallengeResponse | TokenPair:
    ip, ua = _client_meta(request)
    res = await auth.login_step1(body.email, body.password, ip=ip, user_agent=ua)
    if res["stage"] == "totp_required":
        return ChallengeResponse(stage="totp_required", challenge_token=res["challenge_token"])
    return TokenPair(**{k: res[k] for k in ("access_token", "refresh_token", "user")})


@router.post("/login/totp", status_code=200)
async def login_totp(
    body: LoginTotpRequest,
    request: Request,
    auth: AuthServiceDep,
) -> TokenPair:
    ip, ua = _client_meta(request)
    res = await auth.login_step2_totp(body.challenge_token, body.code, ip=ip, user_agent=ua)
    return TokenPair(**{k: res[k] for k in ("access_token", "refresh_token", "user")})


@router.post("/login/recovery", status_code=200)
async def login_recovery(
    body: LoginRecoveryRequest,
    request: Request,
    auth: AuthServiceDep,
) -> TokenPair:
    ip, ua = _client_meta(request)
    res = await auth.login_step2_recovery(
        body.challenge_token, body.recovery_code, ip=ip, user_agent=ua
    )
    return TokenPair(**{k: res[k] for k in ("access_token", "refresh_token", "user")})


@router.post("/refresh", status_code=200)
async def refresh(
    body: RefreshRequest,
    request: Request,
    auth: AuthServiceDep,
) -> TokenPair:
    ip, ua = _client_meta(request)
    res = await auth.refresh_tokens(body.refresh_token, ip=ip, user_agent=ua)
    return TokenPair(**{k: res[k] for k in ("access_token", "refresh_token", "user")})


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, request: Request, auth: AuthServiceDep) -> Response:
    ip, ua = _client_meta(request)
    await auth.logout(body.refresh_token, ip=ip, user_agent=ua)
    return Response(status_code=204)


@router.post("/totp/enroll", status_code=200)
async def totp_enroll(
    user: CurrentUserDep,
    auth: AuthServiceDep,
) -> TotpEnrollResponse:
    res = await auth.totp_enroll(user.id)
    return TotpEnrollResponse(**res)


@router.post("/totp/verify", status_code=200)
async def totp_verify(
    body: TotpVerifyRequest,
    request: Request,
    user: CurrentUserDep,
    auth: AuthServiceDep,
) -> RecoveryCodesResponse:
    ip, ua = _client_meta(request)
    res = await auth.totp_verify(user.id, body.code, ip=ip, user_agent=ua)
    return RecoveryCodesResponse(**res)


@router.post("/totp/disable", status_code=204)
async def totp_disable(
    body: TotpDisableRequest,
    request: Request,
    user: CurrentUserDep,
    auth: AuthServiceDep,
) -> Response:
    ip, ua = _client_meta(request)
    await auth.totp_disable(user.id, body.password, body.code, ip=ip, user_agent=ua)
    return Response(status_code=204)


@router.post("/password/reset/request", status_code=204)
async def password_reset_request(
    body: PasswordResetRequest,
    request: Request,
    auth: AuthServiceDep,
) -> Response:
    ip, ua = _client_meta(request)
    await auth.password_reset_request(body.email, ip=ip, user_agent=ua)
    return Response(status_code=204)


@router.post("/password/reset/confirm", status_code=204)
async def password_reset_confirm(
    body: PasswordResetConfirmRequest,
    request: Request,
    auth: AuthServiceDep,
) -> Response:
    ip, ua = _client_meta(request)
    await auth.password_reset_confirm(body.token, body.new_password, ip=ip, user_agent=ua)
    return Response(status_code=204)


@router.get("/me", status_code=200)
async def me(user: CurrentUserDep) -> UserPublic:
    return UserPublic.model_validate(user, from_attributes=True)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


@router.post("/password/change", status_code=204)
async def password_change(
    body: PasswordChangeRequest,
    request: Request,
    user: CurrentUserDep,
    auth: AuthServiceDep,
) -> Response:
    ip, ua = _client_meta(request)
    await auth.change_password(user.id, body.old_password, body.new_password, ip=ip, user_agent=ua)
    return Response(status_code=204)
