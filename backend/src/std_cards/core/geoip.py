import logging
from pathlib import Path

import maxminddb

from std_cards.config import settings

logger = logging.getLogger(__name__)

_reader: maxminddb.Reader | None = None


def get_reader() -> maxminddb.Reader | None:
    global _reader
    if _reader is not None:
        return _reader
    path = settings.MAXMIND_PATH
    if not Path(path).exists():
        logger.warning("MaxMind DB not found at %s — GeoIP disabled", path)
        return None
    try:
        _reader = maxminddb.open_database(path, mode=maxminddb.MODE_MMAP)
        return _reader
    except Exception:
        logger.exception("Failed to load MaxMind DB")
        return None


def lookup_geo(ip: str | None) -> tuple[str | None, str | None, float | None, float | None]:
    """Returns (country_code, city, lat, lon)."""
    if not ip:
        return None, None, None, None
    reader = get_reader()
    if reader is None:
        return None, None, None, None
    try:
        rec = reader.get(ip)
        if not rec:
            return None, None, None, None
        country = rec.get("country", {}).get("iso_code")
        city_record = rec.get("city", {}).get("names", {}) or {}
        city = (
            city_record.get("en") or next(iter(city_record.values()), None) if city_record else None
        )
        loc = rec.get("location", {})
        return country, city, loc.get("latitude"), loc.get("longitude")
    except Exception:
        logger.exception("GeoIP lookup failed for %s", ip)
        return None, None, None, None
