import logging
from typing import NamedTuple

from ua_parser import user_agent_parser

logger = logging.getLogger(__name__)

_BOT_KEYWORDS = (
    "bot",
    "crawler",
    "spider",
    "facebookexternalhit",
    "googlebot",
    "yandexbot",
)


class UAInfo(NamedTuple):
    device_type: str  # mobile|tablet|desktop|bot|other
    os_family: str
    browser_family: str
    is_bot: bool


def parse_ua(ua_string: str | None) -> UAInfo:
    if not ua_string:
        return UAInfo("other", "", "", False)
    ua_lower = ua_string.lower()
    is_bot = any(b in ua_lower for b in _BOT_KEYWORDS)
    try:
        parsed = user_agent_parser.Parse(ua_string)
        os = parsed["os"]["family"] or ""
        browser = parsed["user_agent"]["family"] or ""
        device = parsed["device"]["family"] or ""
        if is_bot:
            dtype = "bot"
        elif "iPad" in device or "iPad" in ua_string:
            dtype = "tablet"
        elif "iPhone" in device or os in ("iOS", "Android"):
            dtype = "mobile"
        elif device == "Other":
            dtype = "desktop"
        else:
            dtype = "other"
        return UAInfo(dtype, os, browser, is_bot)
    except Exception:
        logger.exception("UA parse failed for: %.100s", ua_string)
        return UAInfo("other", "", "", is_bot)
