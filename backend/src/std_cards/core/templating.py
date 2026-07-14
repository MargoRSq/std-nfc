from datetime import date, datetime
from pathlib import Path

import jinja2

from std_cards.core.translations import get_translations

TEMPLATES_DIR = Path(__file__).parent.parent / "public" / "templates"

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(["html"]),
    enable_async=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _formatdate_ru(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d.%m.%Y")


env.filters["formatdate_ru"] = _formatdate_ru


def render(template_name: str, **context) -> str:
    context.setdefault("t", get_translations())
    return env.get_template(template_name).render(**context)
