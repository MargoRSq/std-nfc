import re
import time
import uuid

import jwt
import pytest

from std_cards.config import settings
from std_cards.core.exceptions import UnauthorizedError
from std_cards.core.security import (
    create_access_token,
    decode_access_token,
    generate_recovery_codes,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_password_verify_roundtrip():
    plain = "SuperSecret123!"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)


def test_verify_password_wrong():
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_verify_password_invalid_hash_returns_false():
    assert not verify_password("anything", "not-a-valid-bcrypt-hash")


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, role="member", token_version=1)
    claims = decode_access_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["role"] == "member"
    assert claims["tv"] == 1
    assert "jti" in claims


def test_access_token_expired():
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, role="member", token_version=1, ttl_minutes=-1)
    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


def test_access_token_invalid_signature():
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, role="member", token_version=1)
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1] + ".invalidsignature"
    with pytest.raises(UnauthorizedError):
        decode_access_token(tampered)


def test_generate_refresh_token_unique():
    tokens = {generate_refresh_token().raw for _ in range(100)}
    assert len(tokens) == 100


def test_hash_refresh_token_deterministic():
    pair = generate_refresh_token()
    assert hash_refresh_token(pair.raw) == hash_refresh_token(pair.raw)


def test_generate_recovery_codes_count_and_format():
    codes = generate_recovery_codes(10)
    assert len(codes) == 10
    pattern = re.compile(r"^[A-Z2-7]{12}$")
    for code in codes:
        assert pattern.match(code), f"Invalid code format: {code}"


def test_decode_rejects_token_without_exp() -> None:
    token = jwt.encode(
        {"sub": "x", "iat": int(time.time()), "tv": 0}, settings.AUTH.SECRET, algorithm="HS256"
    )
    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


def test_decode_rejects_alg_confusion() -> None:
    token = jwt.encode(
        {"sub": "x", "exp": int(time.time()) + 60, "iat": int(time.time()), "tv": 0},
        settings.AUTH.SECRET,
        algorithm="HS512",
    )
    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


def test_password_72byte_boundary() -> None:
    base = "a" * 72
    p1 = base + "X"
    p2 = base + "Y"
    h1 = hash_password(p1)
    assert verify_password(p1, h1) is True
    assert verify_password(p2, h1) is False


def test_password_unicode_long() -> None:
    p = "пароль" * 30
    h = hash_password(p)
    assert verify_password(p, h) is True
    assert verify_password("пароль" * 29, h) is False
