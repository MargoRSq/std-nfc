import re
import secrets

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
DEFAULT_LEN = 6
# Точка разрешена внутри, но не с краю: ".." — риск обхода пути, точка в конце
# теряется/нормализуется частью клиентов. Длина 6-32 — как CHECK в БД.
SLUG_RE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]{4,30}[A-Za-z0-9_-]$")


def gen_slug(n: int = DEFAULT_LEN) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def is_valid_slug(slug: str) -> bool:
    if ".." in slug:
        return False
    return bool(SLUG_RE.match(slug))
