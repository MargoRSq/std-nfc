import base64
import datetime
import hashlib
import logging
import secrets
from typing import NamedTuple
from uuid import UUID, uuid4

import bcrypt
import jwt

from std_cards.config import settings
from std_cards.core.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)


def _bcrypt_prehash(plain: str) -> bytes:
    """SHA-256 + base64 чтобы обойти 72-байтовый лимит bcrypt и поддерживать длинные UTF-8 пароли."""
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(plain: str) -> str:
    pre = _bcrypt_prehash(plain)
    return bcrypt.hashpw(pre, bcrypt.gensalt(rounds=settings.AUTH.BCRYPT_COST)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    pre = _bcrypt_prehash(plain)
    try:
        return bcrypt.checkpw(pre, hashed.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        logger.warning("Invalid bcrypt hash on verify", exc_info=exc)
        return False


def create_access_token(
    user_id: UUID,
    role: str,
    token_version: int,
    ttl_minutes: int | None = None,
) -> str:
    ttl = ttl_minutes if ttl_minutes is not None else settings.AUTH.ACCESS_EXPIRE_MINUTES
    now = datetime.datetime.now(datetime.UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=ttl),
        "jti": uuid4().hex,
        "iss": settings.SERVICE_NAME,
        "aud": "std-cards-api",
    }
    return jwt.encode(payload, settings.AUTH.SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.AUTH.SECRET,
            algorithms=["HS256"],
            options={
                "require": ["exp", "iat", "sub", "tv"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
            audience="std-cards-api",
            issuer=settings.SERVICE_NAME,
        )
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(str(exc)) from exc


class RefreshTokenPair(NamedTuple):
    raw: str
    hashed: str


def generate_refresh_token() -> RefreshTokenPair:
    raw = secrets.token_urlsafe(32)
    hashed = hash_refresh_token(raw)
    return RefreshTokenPair(raw=raw, hashed=hashed)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_recovery_codes(n: int = 10) -> list[str]:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
    return ["".join(secrets.choice(alphabet) for _ in range(12)) for _ in range(n)]
