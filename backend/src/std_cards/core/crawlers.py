import re

# Парсеры превью ссылок в мессенджерах. Только им публичная карточка отдаётся
# без X-Robots-Tag: Apple LinkPresentation трактует noindex строго и отказывается
# тянуть og:image, а iMessage ходит именно как facebookexternalhit + Twitterbot.
# Всё остальное (браузеры, поисковики, неизвестные боты) получает noindex —
# браузеры директиву игнорируют, так что ложное срабатывание безвредно.
_LINK_PREVIEW_RE = re.compile(
    r"facebookexternalhit|facebot|twitterbot|telegrambot|whatsapp|slackbot|"
    r"slack-imgproxy|discordbot|linkedinbot|pinterest|redditbot|skypeuripreview|"
    r"viber|vkshare",
    re.IGNORECASE,
)

NOINDEX = "noindex, nofollow"


def wants_link_preview(user_agent: str | None) -> bool:
    if not user_agent:
        return False
    return bool(_LINK_PREVIEW_RE.search(user_agent))
