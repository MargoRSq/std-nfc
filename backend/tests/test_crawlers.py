import pytest

from std_cards.core.crawlers import wants_link_preview

IMESSAGE_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 "
    "(KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 "
    "facebookexternalhit/1.1 Facebot Twitterbot/1.0"
)


@pytest.mark.parametrize(
    "ua",
    [
        IMESSAGE_UA,
        "TelegramBot (like TwitterBot)",
        "WhatsApp/2.23.20.0 A",
        "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
        "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    ],
)
def test_link_preview_parsers_recognised(ua: str):
    assert wants_link_preview(ua) is True


@pytest.mark.parametrize(
    "ua",
    [
        None,
        "",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/15.1 Safari/605.1.15 (Applebot/0.1)",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/147.0.0.0 Safari/537.36",
    ],
)
def test_everything_else_gets_noindex(ua: str | None):
    assert wants_link_preview(ua) is False
