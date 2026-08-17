"""Единый формат градиентов: ключи from/to

Revision ID: 0029_normalize_gradients
Revises: 0028_strip_blank_contacts
Create Date: 2026-08-17

В базе накопились три формата: `{from,to}`, легаси `{start,end}` и
`{from_color,to_color}` — последний писался при «Назначить шаблон», потому что
model_dump разворачивал вложенную модель по именам полей, а не по алиасам.
card.html и превью читают только `from`/`to`, поэтому такие карточки рисовались
дефолтным сине-фиолетовым градиентом вместо цветов шаблона.

`jsonb_exists(...)` вместо оператора `?`: вопросительный знак ломается на
драйверах, которые считают его плейсхолдером.
"""

import sqlalchemy as sa
from alembic import op

revision = "0029_normalize_gradients"
down_revision = "0028_strip_blank_contacts"
branch_labels = None
depends_on = None

# Канонический ключ → легаси-имена, из которых его берём.
_RENAMES = (("from", ("from_color", "start")), ("to", ("to_color", "end")))


def _normalize_column(table: str, column: str) -> None:
    for canonical, sources in _RENAMES:
        for src in sources:
            op.execute(
                sa.text(
                    f"UPDATE {table} SET {column} = "
                    f"({column} - :src) || jsonb_build_object(:canonical, {column} -> :src) "
                    f"WHERE jsonb_exists({column}, :src) "
                    f"  AND NOT jsonb_exists({column}, :canonical)"
                ).bindparams(src=src, canonical=canonical)
            )
            # Легаси-ключ рядом с уже существующим каноническим — просто выкидываем.
            op.execute(
                sa.text(
                    f"UPDATE {table} SET {column} = {column} - :src "
                    f"WHERE jsonb_exists({column}, :src)"
                ).bindparams(src=src)
            )


def _normalize_template_styles(key: str) -> None:
    for canonical, sources in _RENAMES:
        for src in sources:
            op.execute(
                sa.text(
                    "UPDATE templates SET default_styles = jsonb_set("
                    "  default_styles, ARRAY[:key],"
                    "  ((default_styles -> :key) - :src)"
                    "  || jsonb_build_object(:canonical, default_styles -> :key -> :src)) "
                    "WHERE jsonb_exists(default_styles, :key) "
                    "  AND jsonb_exists(default_styles -> :key, :src) "
                    "  AND NOT jsonb_exists(default_styles -> :key, :canonical)"
                ).bindparams(key=key, src=src, canonical=canonical)
            )
            op.execute(
                sa.text(
                    "UPDATE templates SET default_styles = jsonb_set("
                    "  default_styles, ARRAY[:key], (default_styles -> :key) - :src) "
                    "WHERE jsonb_exists(default_styles, :key) "
                    "  AND jsonb_exists(default_styles -> :key, :src)"
                ).bindparams(key=key, src=src)
            )


def upgrade() -> None:
    _normalize_column("cards", "bg_gradient")
    _normalize_column("cards", "avatar_gradient")
    _normalize_template_styles("bg_gradient")
    _normalize_template_styles("avatar_gradient")


def downgrade() -> None:
    """Обратного хода нет: исходный формат каждой строки не сохраняем.

    Данные при этом не теряются — `from`/`to` читают все версии рендера.
    """
