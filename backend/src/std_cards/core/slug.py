import re
import secrets

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
DEFAULT_LEN = 6
SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def gen_slug(n: int = DEFAULT_LEN) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def is_valid_slug(slug: str) -> bool:
    return bool(SLUG_RE.match(slug))
