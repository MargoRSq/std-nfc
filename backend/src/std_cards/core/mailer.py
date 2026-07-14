"""Отправка писем через SMTP. Без SMTP_HOST почта отключена — вызовы no-op."""

import logging
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from std_cards.config import settings

logger = logging.getLogger(__name__)

SEND_TIMEOUT = 20.0
# Белая версия: шапка письма тёмно-синяя, тёмный вариант на ней не виден.
LOGO_PATH = Path(__file__).parent.parent / "public" / "og-emblem-white.png"
LOGO_CID = "std-logo"


def mail_enabled() -> bool:
    return bool(settings.SMTP.HOST)


async def send_mail(
    to: str, subject: str, text: str, html: str | None = None, *, embed_logo: bool = False
) -> None:
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
        if embed_logo and LOGO_PATH.exists():
            # Логотип вкладываем в письмо (cid), а не ссылкой: внешние картинки
            # почтовики блокируют по умолчанию — логотип бы не отобразился.
            html_part = message.get_payload()[-1]
            html_part.add_related(
                LOGO_PATH.read_bytes(),
                maintype="image",
                subtype="png",
                cid=f"<{LOGO_CID}>",
                filename="std.png",
            )

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


def _reset_html(reset_url: str) -> str:
    """Вёрстка письма: таблицы + инлайн-стили — единственное, что одинаково

    рендерят Outlook, Gmail и Mail.ru. Флексы/классы/внешний CSS там не работают.
    """
    return f"""\
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background:#F5F5F5;padding:32px 12px;font-family:Arial,Helvetica,sans-serif">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="max-width:520px;background:#FFFFFF;border-radius:16px;overflow:hidden">
      <tr>
        <td align="center" style="background:#1F1E5E;padding:28px 24px">
          <img src="cid:{LOGO_CID}" width="72" height="72" alt="СТД РФ"
               style="display:block;border:0;outline:none;text-decoration:none">
          <div style="color:#FFFFFF;font-size:15px;font-weight:bold;padding-top:12px;
                      letter-spacing:0.3px">
            Союз театральных деятелей<br>Российской Федерации
          </div>
        </td>
      </tr>
      <tr>
        <td style="padding:32px 32px 8px">
          <div style="font-size:22px;font-weight:bold;color:#1F1E5E;padding-bottom:12px">
            Смена пароля
          </div>
          <div style="font-size:15px;line-height:1.55;color:#333333">
            Здравствуйте! Для вашей учётной записи в системе электронных удостоверений
            запрошена смена пароля. Нажмите кнопку ниже, чтобы задать новый.
          </div>
        </td>
      </tr>
      <tr>
        <td align="center" style="padding:24px 32px 8px">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td align="center" style="background:#1F1E5E;border-radius:28px">
                <a href="{reset_url}"
                   style="display:inline-block;padding:14px 38px;color:#FFFFFF;font-size:16px;
                          font-weight:bold;text-decoration:none;border-radius:28px">
                  Сменить пароль
                </a>
              </td>
            </tr>
          </table>
        </td>
      </tr>
      <tr>
        <td style="padding:16px 32px 0">
          <div style="font-size:12px;color:#888888;padding-bottom:6px">
            Если кнопка не работает, скопируйте ссылку в браузер:
          </div>
          <div style="font-size:12px;color:#1F1E5E;word-break:break-all">{reset_url}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:24px 32px 32px">
          <div style="border-top:1px solid #EEEEEE;padding-top:16px;font-size:12px;
                      line-height:1.6;color:#888888">
            Ссылка действует 2 часа и срабатывает один раз.<br>
            Если вы не запрашивали смену пароля — просто проигнорируйте это письмо,
            пароль останется прежним.
          </div>
        </td>
      </tr>
    </table>
  </td></tr>
</table>"""


async def send_password_reset(to: str, reset_url: str) -> None:
    text = (
        "Здравствуйте!\n\n"
        "Для смены пароля в системе электронных удостоверений СТД РФ перейдите по ссылке:\n"
        f"{reset_url}\n\n"
        "Ссылка действует 2 часа и срабатывает один раз.\n"
        "Если вы не запрашивали смену пароля — просто проигнорируйте это письмо.\n"
    )
    await send_mail(
        to,
        "Смена пароля — удостоверения СТД РФ",
        text,
        _reset_html(reset_url),
        embed_logo=True,
    )
