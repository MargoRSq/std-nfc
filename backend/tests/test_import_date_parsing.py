from datetime import date, datetime

import pytest

from std_cards.services.import_service import coerce_date, coerce_year


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        (datetime(1987, 10, 13, 0, 0), date(1987, 10, 13)),
        (date(1987, 10, 13), date(1987, 10, 13)),
        # «Дата вступления» в файлах СТД приходит голым годом
        (2025, date(2025, 1, 1)),
        ("2025", date(2025, 1, 1)),
        ("с 2025", date(2025, 1, 1)),
        ("2025 г.", date(2025, 1, 1)),
        ("13.10.1987", date(1987, 10, 13)),
        ("1987-10-13", date(1987, 10, 13)),
        ("13/10/1987", date(1987, 10, 13)),
    ],
)
def test_coerce_date(raw, expected):
    assert coerce_date(raw, field="Дата вступления") == expected


@pytest.mark.parametrize("raw", ["-", "—", "нет", "не указано", "н/д"])
def test_coerce_date_treats_placeholders_as_empty(raw):
    assert coerce_date(raw, field="Дата вступления") is None


@pytest.mark.parametrize("raw", ["не дата", "13.13.1987", 12, 99999])
def test_coerce_date_rejects_garbage(raw):
    with pytest.raises(ValueError, match="Дата вступления"):
        coerce_date(raw, field="Дата вступления")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        (2026, 2026),
        ("2026", 2026),
        ("в 2026", 2026),
        (date(2026, 5, 1), 2026),
    ],
)
def test_coerce_year(raw, expected):
    assert coerce_year(raw, field="Год исключения") == expected


def test_coerce_year_treats_placeholders_as_empty():
    assert coerce_year("—", field="Год исключения") is None


@pytest.mark.parametrize("raw", ["позапрошлый", 1500, "20261"])
def test_coerce_year_rejects_garbage(raw):
    with pytest.raises(ValueError, match="Год исключения"):
        coerce_year(raw, field="Год исключения")


def test_row_to_card_create_keeps_logo_empty():
    """Пустой logo_key рендерит широкую брендовую плашку СТД; preset:std дал бы
    мелкий квадрат на белой подложке — дефолт при импорте не проставляем."""
    from std_cards.services.import_service import ImportService

    svc = ImportService.__new__(ImportService)
    card = svc._row_to_card_create(("Иванов", "Иван", "Иванович", "MBR-1"), template=None)

    assert card.logo_key is None
