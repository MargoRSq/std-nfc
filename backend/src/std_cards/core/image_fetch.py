"""Загрузка фото по ссылке для импорта: прямые URL и публичные ссылки Яндекс.Диска."""

import io
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from PIL import Image

YANDEX_PUBLIC_HOSTS = {
    "disk.yandex.ru",
    "disk.yandex.com",
    "disk.yandex.by",
    "disk.yandex.kz",
    "disk.360.yandex.ru",
    "yadi.sk",
}
YANDEX_DOWNLOAD_API = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
MAX_IMAGE_BYTES = 15 * 1024 * 1024
FETCH_TIMEOUT = 30.0
# Хостинги картинок (в т.ч. Wikimedia, picsum) отдают 403 на дефолтный UA httpx.
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

_CONTENT_TYPE_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ImageFetchError(Exception):
    pass


def _assert_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ImageFetchError(f"неподдерживаемая ссылка: {parsed.scheme or url[:40]}")
    host = parsed.hostname
    if not host:
        raise ImageFetchError(f"ссылка без домена: {url[:40]}")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ImageFetchError(f"домен не резолвится: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ImageFetchError(f"внутренний адрес недоступен для загрузки: {host}")


async def _resolve_yandex_href(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(YANDEX_DOWNLOAD_API, params={"public_key": url})
    if resp.status_code != 200:
        raise ImageFetchError(
            f"Яндекс.Диск вернул {resp.status_code} — ссылка должна быть публичной"
        )
    href = resp.json().get("href")
    if not href:
        raise ImageFetchError("Яндекс.Диск не вернул ссылку на скачивание")
    return href


def detect_content_type(raw: bytes) -> str:
    try:
        fmt = (Image.open(io.BytesIO(raw)).format or "").upper()
    except Exception as exc:
        raise ImageFetchError(f"файл не является изображением: {exc}") from exc
    if fmt not in _CONTENT_TYPE_BY_FORMAT:
        raise ImageFetchError(f"неподдерживаемый формат: {fmt or 'неизвестный'}")
    return _CONTENT_TYPE_BY_FORMAT[fmt]


async def fetch_image(url: str) -> tuple[bytes, str]:
    """Скачать изображение по ссылке. Возвращает (bytes, content_type)."""
    url = url.strip()
    _assert_public_host(url)
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT, follow_redirects=True, headers=HTTP_HEADERS
    ) as client:
        target = url
        if (urlparse(url).hostname or "").lower() in YANDEX_PUBLIC_HOSTS:
            target = await _resolve_yandex_href(client, url)
        chunks: list[bytes] = []
        size = 0
        async with client.stream("GET", target) as resp:
            if resp.status_code != 200:
                raise ImageFetchError(f"HTTP {resp.status_code} при скачивании")
            async for chunk in resp.aiter_bytes():
                size += len(chunk)
                if size > MAX_IMAGE_BYTES:
                    raise ImageFetchError(f"файл больше {MAX_IMAGE_BYTES // 1024 // 1024} МБ")
                chunks.append(chunk)
    raw = b"".join(chunks)
    return raw, detect_content_type(raw)
