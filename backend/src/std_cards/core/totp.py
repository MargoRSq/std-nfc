import base64
import hmac
import io
import time

import pyotp
import qrcode

from std_cards.config import settings


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str, issuer: str | None = None) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=issuer or settings.AUTH.TOTP_ISSUER,
    )


def verify_totp_code(secret: str, code: str, *, valid_window: int = 1) -> bool:
    """Проверка TOTP кода с tolerance ±valid_window 30s-окон (без replay-защиты).

    Предпочитай verify_totp_step — она возвращает period index для persist
    users.last_totp_step и отвергает повторное использование кода.
    """
    return pyotp.TOTP(secret).verify(code, valid_window=valid_window)


def current_totp_step(*, for_time: float | None = None) -> int:
    return int((for_time if for_time is not None else time.time()) // 30)


def verify_totp_step(
    secret: str,
    code: str,
    *,
    valid_window: int = 1,
    after_step: int | None = None,
    for_time: float | None = None,
) -> int | None:
    """Проверяет TOTP-код и возвращает matched 30s-period index, либо None.

    Replay-защита: шаги ≤ after_step отвергаются — один код валиден не более
    одного раза в цепочке. Caller ОБЯЗАН persist возвращённый step в
    users.last_totp_step после успеха.
    """
    totp = pyotp.TOTP(secret)
    current = current_totp_step(for_time=for_time)
    expected = str(code).strip()
    for offset in range(-valid_window, valid_window + 1):
        step = current + offset
        if after_step is not None and step <= after_step:
            continue
        if hmac.compare_digest(totp.at(step * 30), expected):
            return step
    return None


def qr_code_png_base64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
