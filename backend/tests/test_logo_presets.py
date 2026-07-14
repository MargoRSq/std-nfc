import pytest

from std_cards.logo_presets import (
    DEFAULT_PRESET_ID,
    PRESETS,
    default_logo_key,
    is_preset_key,
    is_valid_logo_key,
    make_preset_key,
    preset_id_from_key,
)


def test_std_preset_registered() -> None:
    assert "std" in PRESETS
    assert PRESETS["std"].id == "std"
    assert PRESETS["std"].name == "СТД РФ"


def test_default_preset_id_is_std() -> None:
    assert DEFAULT_PRESET_ID == "std"
    assert default_logo_key() == "preset:std"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("preset:std", True),
        ("preset:other", True),
        ("cards/abc/logo.webp", False),
        ("", False),
        (None, False),
    ],
)
def test_is_preset_key(value: str | None, expected: bool) -> None:
    assert is_preset_key(value) is expected


def test_preset_id_from_key() -> None:
    assert preset_id_from_key("preset:std") == "std"
    assert preset_id_from_key("preset:foo-bar") == "foo-bar"


def test_make_preset_key() -> None:
    assert make_preset_key("std") == "preset:std"


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, True),
        ("preset:std", True),
        ("cards/abc-uuid/logo-deadbeef.webp", True),
        ("preset:nonexistent", False),
        ("garbage", False),
        ("http://example.com/logo.png", False),
        ("/logos/std.png", False),
        ("", False),
    ],
)
def test_is_valid_logo_key(value: str | None, expected: bool) -> None:
    assert is_valid_logo_key(value) is expected
