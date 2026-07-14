from dataclasses import dataclass


@dataclass(frozen=True)
class PresetMeta:
    id: str
    name: str


PRESET_PREFIX = "preset:"

PRESETS: dict[str, PresetMeta] = {
    "std": PresetMeta(id="std", name="СТД РФ"),
}

DEFAULT_PRESET_ID = "std"


def is_preset_key(value: str | None) -> bool:
    return bool(value) and value.startswith(PRESET_PREFIX)  # type: ignore[union-attr]


def preset_id_from_key(value: str) -> str:
    return value[len(PRESET_PREFIX) :]


def make_preset_key(preset_id: str) -> str:
    return f"{PRESET_PREFIX}{preset_id}"


def is_valid_logo_key(value: str | None) -> bool:
    if value is None:
        return True
    if is_preset_key(value):
        return preset_id_from_key(value) in PRESETS
    return value.startswith("cards/")


def default_logo_key() -> str:
    return make_preset_key(DEFAULT_PRESET_ID)
