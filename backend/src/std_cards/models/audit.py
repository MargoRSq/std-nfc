from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class AuditAction(StrEnum):
    LOGIN_SUCCESS = "login.success"
    LOGIN_FAIL = "login.fail"
    LOGOUT = "logout"
    TOTP_VERIFY = "totp.verify"
    TOTP_FAIL = "totp.fail"
    RECOVERY_USE = "recovery.use"
    PASSWORD_RESET_REQUEST = "password.reset_request"
    PASSWORD_RESET_CONFIRM = "password.reset_confirm"
    PASSWORD_CHANGE = "password.change"
    PASSWORD_RESET = "password.reset"
    TOTP_ENROLL = "totp.enroll"
    TOTP_DISABLE = "totp.disable"
    CARD_CREATE = "card.create"
    CARD_UPDATE = "card.update"
    CARD_DELETE = "card.delete"
    CARD_BULK_EXPORT = "card.bulk_export"
    ANALYTICS_REPORT_EXPORT = "analytics.report_export"
    TEMPLATE_CREATE = "template.create"
    TEMPLATE_UPDATE = "template.update"
    TEMPLATE_DELETE = "template.delete"
    IMPORT_START = "import.start"
    IMPORT_FINISH = "import.finish"
    ADMIN_CREATE = "admin.create"
    ADMIN_UPDATE = "admin.update"
    ADMIN_DELETE = "admin.delete"
    ADMIN_RESET_PASSWORD = "admin.reset_password"
    ADMIN_RESET_2FA = "admin.reset_2fa"
    FORCE_LOGOUT = "admin.force_logout"


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    actor_id: UUID | None
    actor_email: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    ip: str | None
    user_agent: str | None
    diff: dict[str, Any] | None

    @field_validator("ip", mode="before")
    @classmethod
    def _ip_to_str(cls, v):
        if v is None:
            return None
        return str(v)
