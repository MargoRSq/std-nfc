import base64
import re
from urllib.parse import unquote

import pyotp

from std_cards.core.totp import (
    current_totp_step,
    generate_totp_secret,
    provisioning_uri,
    qr_code_png_base64,
    verify_totp_code,
    verify_totp_step,
)


def test_generate_secret_format():
    secret = generate_totp_secret()
    assert re.match(r"^[A-Z2-7]{32}$", secret), f"Unexpected format: {secret}"


def test_provisioning_uri_contains_issuer_and_email():
    secret = generate_totp_secret()
    email = "user@example.com"
    uri = provisioning_uri(secret, email)
    decoded_uri = unquote(uri)
    assert email in decoded_uri
    assert "otpauth://totp/" in uri


def test_verify_correct_code():
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_totp_code(secret, code)


def test_verify_wrong_code():
    secret = generate_totp_secret()
    assert not verify_totp_code(secret, "000000")


def test_verify_step_returns_matched_period():
    secret = generate_totp_secret()
    now = 1_700_000_000.0
    code = pyotp.TOTP(secret).at(int(now))
    step = verify_totp_step(secret, code, for_time=now)
    assert step == current_totp_step(for_time=now)


def test_verify_step_rejects_replay():
    secret = generate_totp_secret()
    now = 1_700_000_000.0
    code = pyotp.TOTP(secret).at(int(now))
    step = verify_totp_step(secret, code, for_time=now)
    # same code, now persisted as last step → must be rejected
    assert verify_totp_step(secret, code, after_step=step, for_time=now) is None


def test_verify_step_wrong_code():
    secret = generate_totp_secret()
    assert verify_totp_step(secret, "000000", for_time=1_700_000_000.0) is None


def test_qr_code_png_base64_returns_data_uri_or_base64():
    secret = generate_totp_secret()
    uri = provisioning_uri(secret, "user@example.com")
    result = qr_code_png_base64(uri)
    assert result
    decoded = base64.b64decode(result)
    assert decoded[:4] == b"\x89PNG"
