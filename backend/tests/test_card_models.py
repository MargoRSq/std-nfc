import pytest
from pydantic import ValidationError

from std_cards.models.card import CardCreate, CardUpdate


def _create_kwargs(**extra) -> dict:
    return dict(
        last_name="Иванов",
        first_name="Иван",
        membership_no="X1",
        category_id=1,
        **extra,
    )


@pytest.mark.parametrize(
    "logo_key",
    [None, "preset:std", "cards/abc/logo-deadbeef.webp"],
)
def test_card_create_accepts_valid_logo_key(logo_key: str | None) -> None:
    payload = _create_kwargs(logo_key=logo_key) if logo_key is not None else _create_kwargs()
    if logo_key is not None:
        payload["logo_key"] = logo_key
    model = CardCreate(**payload)
    assert model.logo_key == logo_key


@pytest.mark.parametrize(
    "logo_key",
    ["preset:nonexistent", "garbage", "http://example.com/logo.png", "/logos/std.png"],
)
def test_card_create_rejects_invalid_logo_key(logo_key: str) -> None:
    payload = _create_kwargs(logo_key=logo_key)
    with pytest.raises(ValidationError):
        CardCreate(**payload)


@pytest.mark.parametrize(
    "logo_key",
    [None, "preset:std", "cards/abc/logo-x.webp"],
)
def test_card_update_accepts_valid_logo_key(logo_key: str | None) -> None:
    model = CardUpdate(logo_key=logo_key)
    assert model.logo_key == logo_key


@pytest.mark.parametrize(
    "logo_key",
    ["preset:nonexistent", "garbage", "http://example.com/logo.png"],
)
def test_card_update_rejects_invalid_logo_key(logo_key: str) -> None:
    with pytest.raises(ValidationError):
        CardUpdate(logo_key=logo_key)


def test_card_update_unset_logo_key_is_excluded() -> None:
    model = CardUpdate(last_name="X")
    dumped = model.model_dump(exclude_unset=True)
    assert "logo_key" not in dumped


def test_card_update_explicit_null_logo_key_is_included() -> None:
    model = CardUpdate(logo_key=None)
    dumped = model.model_dump(exclude_unset=True)
    assert dumped == {"logo_key": None}


def test_blank_contact_blocks_are_dropped() -> None:
    """Пустой блок доезжал до публичной карточки пилюлей «None»."""
    model = CardUpdate(
        contacts=[
            {"type": None, "value": ""},
            {"type": "phone", "value": "+7 495 650-28-46"},
            {"type": None, "value": "   "},
        ]
    )
    assert model.contacts is not None
    assert [c.value for c in model.contacts] == ["+7 495 650-28-46"]


def test_labelled_block_without_value_is_kept() -> None:
    """Служебный блок с названием, но пока без значения, терять нельзя."""
    model = CardUpdate(internal_blocks=[{"type": None, "value": "", "label": "Паспорт"}])
    assert model.internal_blocks is not None
    assert len(model.internal_blocks) == 1


def test_card_create_drops_blank_contacts() -> None:
    model = CardCreate(**_create_kwargs(contacts=[{"type": None, "value": ""}]))
    assert model.contacts == []
