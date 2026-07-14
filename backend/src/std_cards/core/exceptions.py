from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExceptionResponse:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    query: dict[str, Any] = field(default_factory=dict)


class APIException(Exception):
    """Базовый класс HTTP-исключений с структурированным ответом.

    Subclass + override STATUS_CODE/CODE/MESSAGE.
    Глобальный handler в api/exception_handlers.py превращает в JSON ответ.
    """

    STATUS_CODE: int = 500
    CODE: str = "internal_error"
    MESSAGE: str = "Internal server error"

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.MESSAGE
        self.details = details or {}
        super().__init__(self.message)

    @property
    def exception_response(self) -> ExceptionResponse:
        return ExceptionResponse(code=self.CODE, message=self.message, details=self.details)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self.exception_response)


class NotFoundError(APIException):
    STATUS_CODE = 404
    CODE = "not_found"
    MESSAGE = "Resource not found"


class UnauthorizedError(APIException):
    STATUS_CODE = 401
    CODE = "unauthorized"
    MESSAGE = "Authentication required"


class InvalidCredentialsError(UnauthorizedError):
    CODE = "invalid_credentials"
    MESSAGE = "Неверная почта или пароль"


class RefreshReuseError(UnauthorizedError):
    CODE = "refresh_reuse_detected"
    MESSAGE = "Suspicious activity detected, please re-login"


class ForbiddenError(APIException):
    STATUS_CODE = 403
    CODE = "forbidden"
    MESSAGE = "Access denied"


class ConflictError(APIException):
    STATUS_CODE = 409
    CODE = "conflict"
    MESSAGE = "Resource conflict"


class ValidationFailedError(APIException):
    STATUS_CODE = 422
    CODE = "validation_failed"
    MESSAGE = "Request validation failed"


class RateLimitedError(APIException):
    STATUS_CODE = 429
    CODE = "rate_limited"
    MESSAGE = "Too many requests"


class CardInvalidError(APIException):
    STATUS_CODE = 410
    CODE = "card_invalid"
    MESSAGE = "Удостоверение недействительно"
