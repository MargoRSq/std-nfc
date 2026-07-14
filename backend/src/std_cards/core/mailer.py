"""Отправка писем через SMTP. Без SMTP_HOST почта отключена — вызовы no-op."""

import logging
from email.message import EmailMessage

import aiosmtplib

from std_cards.config import settings

logger = logging.getLogger(__name__)

SEND_TIMEOUT = 20.0


def mail_enabled() -> bool:
    return bool(settings.SMTP.HOST)


async def send_mail(to: str, subject: str, text: str, html: str | None = None) -> None:
    if not mail_enabled():
        logger.warning("SMTP не настроен (SMTP_HOST пуст), письмо для %s не отправлено", to)
        return
    message = EmailMessage()
    message["From"] = settings.SMTP.FROM or settings.SMTP.USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP.HOST,
        port=settings.SMTP.PORT,
        username=settings.SMTP.USER or None,
        password=settings.SMTP.PASSWORD or None,
        use_tls=settings.SMTP.SSL,
        start_tls=not settings.SMTP.SSL,
        timeout=SEND_TIMEOUT,
    )
    logger.info("Письмо отправлено: %s (%s)", to, subject)


async def send_password_reset(to: str, reset_url: str) -> None:
    text = (
        "Здравствуйте!\n\n"
        "Для смены пароля в системе электронных удостоверений СТД РФ перейдите по ссылке:\n"
        f"{reset_url}\n\n"
        "Ссылка действует ограниченное время и работает один раз.\n"
        "Если вы не запрашивали смену пароля — просто проигнорируйте это письмо.\n"
    )
    html = (
        '<div style="font-family:Arial,sans-serif;font-size:15px;color:#1F1E5E">'
        "<p>Здравствуйте!</p>"
        "<p>Для смены пароля в системе электронных удостоверений СТД РФ "
        "перейдите по ссылке:</p>"
        f'<p><a href="{reset_url}" style="color:#1F1E5E">Сменить пароль</a></p>'
        f'<p style="font-size:13px;color:#666">{reset_url}</p>'
        '<p style="font-size:13px;color:#666">Ссылка действует ограниченное время и '
        "работает один раз. Если вы не запрашивали смену пароля — проигнорируйте письмо.</p>"
        "</div>"
    )
    await send_mail(to, "Смена пароля — удостоверения СТД РФ", text, html)
