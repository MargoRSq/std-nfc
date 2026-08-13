"""Чистка пустых контакт-блоков в карточках

Revision ID: 0028_strip_blank_contacts
Revises: 0027_categories_hidden
Create Date: 2026-08-12

Пустой блок (нажали «Добавить контакт» и сохранили) рисовался на публичной
карточке пилюлей «None». Валидация теперь такие блоки не пропускает, здесь
чистим уже сохранённые.
"""

from alembic import op

revision = "0028_strip_blank_contacts"
down_revision = "0027_categories_hidden"
branch_labels = None
depends_on = None

_STRIP = """
UPDATE cards
SET {col} = COALESCE(
    (
        SELECT jsonb_agg(b)
        FROM jsonb_array_elements({col}) AS b
        WHERE btrim(COALESCE(b->>'value', '')) <> ''
           OR btrim(COALESCE(b->>'label', '')) <> ''
    ),
    '[]'::jsonb
)
WHERE jsonb_typeof({col}) = 'array'
  AND EXISTS (
      SELECT 1
      FROM jsonb_array_elements({col}) AS b
      WHERE btrim(COALESCE(b->>'value', '')) = ''
        AND btrim(COALESCE(b->>'label', '')) = ''
  )
"""


def upgrade() -> None:
    for col in ("contacts", "internal_blocks"):
        op.execute(_STRIP.format(col=col))


def downgrade() -> None:
    pass
