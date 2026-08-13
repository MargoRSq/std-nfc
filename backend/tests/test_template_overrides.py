from datetime import UTC, datetime
from uuid import uuid4

from std_cards.models.template import TemplateDB
from std_cards.services.card_service import compute_template_overrides


def _template(**styles) -> TemplateDB:
    now = datetime.now(UTC)
    return TemplateDB(
        id=uuid4(),
        name="Участники",
        category_id=1,
        default_fields={},
        default_styles=styles,
        custom_field_schema=[],
        created_by=None,
        is_default=False,
        created_at=now,
        updated_at=now,
    )


def _filled_card_args() -> dict:
    return dict(
        current_bg_kind="solid",
        current_bg_color="#111111",
        current_bg_gradient=None,
        current_photo_shape="circle",
        current_chairman="В.Л. Машков",
        current_region="Москва",
        current_logo_key="preset:std",
        current_logo_shape="circle",
        current_avatar_color="#222222",
        current_avatar_gradient=None,
        current_contacts=[{"type": "phone", "value": "+7 999"}],
        current_label_set=[{"key": "a", "label": "A", "value": "1"}],
    )


def test_filled_card_untouched_without_force() -> None:
    tpl = _template(bg_kind="solid", bg_color="#ABCDEF", photo_shape="square")
    assert compute_template_overrides(template=tpl, **_filled_card_args()) == {}


def test_force_overwrites_styles() -> None:
    tpl = _template(bg_kind="solid", bg_color="#ABCDEF", photo_shape="square", logo_shape="square")
    update = compute_template_overrides(template=tpl, force=True, **_filled_card_args())
    assert update["bg_color"] == "#ABCDEF"
    assert update["photo_shape"] == "square"
    assert update["logo_shape"] == "square"


def test_force_clears_opposite_background() -> None:
    """Шаблон с градиентом должен сбросить сплошной цвет, иначе карточка не перекрасится."""
    tpl = _template(bg_kind="gradient", bg_gradient={"from": "#1F1E5E", "to": "#798BFF"})
    update = compute_template_overrides(template=tpl, force=True, **_filled_card_args())
    assert update["bg_kind"] == "gradient"
    assert update["bg_color"] is None
    assert update["bg_gradient"].from_color == "#1F1E5E"

    solid_tpl = _template(bg_kind="solid", bg_color="#ABCDEF")
    args = _filled_card_args()
    args["current_bg_kind"] = "gradient"
    args["current_bg_gradient"] = {"from": "#000000", "to": "#FFFFFF", "angle": 135}
    update = compute_template_overrides(template=solid_tpl, force=True, **args)
    assert update["bg_kind"] == "solid"
    assert update["bg_gradient"] is None


def test_force_keeps_member_data() -> None:
    tpl = _template()
    tpl = tpl.model_copy(
        update={"default_fields": {"chairman": "Другой", "region": "Тверь", "contacts": []}}
    )
    update = compute_template_overrides(template=tpl, force=True, **_filled_card_args())
    assert "chairman" not in update
    assert "region" not in update
    assert "contacts" not in update
