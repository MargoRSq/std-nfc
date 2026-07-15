"""Дефолтный шаблон «По умолчанию» → «Стандартная» (по имени категории)

Revision ID: 0024_rename_default_template
Revises: 0023_standard_category
Create Date: 2026-07-15

Категория новых членов называется «Стандартная», а шаблон, который её задаёт, —
«По умолчанию». В диалоге «Назначить шаблон» это читается как разные вещи.
Приводим имя шаблона к имени категории. Пользовательские шаблоны не трогаем.
"""

import sqlalchemy as sa
from alembic import op

revision = "0024_rename_default_template"
down_revision = "0023_standard_category"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text("""
            UPDATE templates SET name = 'Стандартная'
            WHERE name = 'По умолчанию'
              AND NOT EXISTS (SELECT 1 FROM templates WHERE name = 'Стандартная')
        """)
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("""
            UPDATE templates SET name = 'По умолчанию'
            WHERE name = 'Стандартная'
              AND NOT EXISTS (SELECT 1 FROM templates WHERE name = 'По умолчанию')
        """)
    )
