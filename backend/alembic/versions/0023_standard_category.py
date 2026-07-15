"""Категория «Стандартная» — дефолт для новых членов вместо «Бронзовых»

Revision ID: 0023_standard_category
Revises: 0022_unaccent_schema_qualified
Create Date: 2026-07-15

Категорий было четыре — все «уровни» (Платиновые…Бронзовые). Шаблон
«По умолчанию» (фирменный синий градиент) был привязан к Бронзовым, поэтому
член, созданный без выбора категории, молча становился «Бронзовым».
Добавляем нейтральную «Стандартную» (фирменный синий) и вешаем на неё
дефолтный шаблон.
"""

import sqlalchemy as sa
from alembic import op

revision = "0023_standard_category"
down_revision = "0022_unaccent_schema_qualified"
branch_labels = None
depends_on = None

BRAND_BLUE = "#1F1E5E"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            INSERT INTO categories (code, name_ru, order_idx, color_hex)
            VALUES ('standard', 'Стандартная', 0, :color)
            ON CONFLICT (code) DO UPDATE SET color_hex = EXCLUDED.color_hex
        """),
        {"color": BRAND_BLUE},
    )
    # Дефолтные шаблоны переводим на «Стандартную»: они и так синие,
    # но числились Бронзовыми. Пользовательские шаблоны уровней не трогаем.
    conn.execute(
        sa.text("""
            UPDATE templates SET category_id = (SELECT id FROM categories WHERE code = 'standard')
            WHERE is_default = true
        """)
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE templates SET category_id = (SELECT id FROM categories WHERE code = 'bronze')
            WHERE category_id = (SELECT id FROM categories WHERE code = 'standard')
        """)
    )
    conn.execute(
        sa.text("""
            UPDATE cards SET category_id = (SELECT id FROM categories WHERE code = 'bronze')
            WHERE category_id = (SELECT id FROM categories WHERE code = 'standard')
        """)
    )
    conn.execute(sa.text("DELETE FROM categories WHERE code = 'standard'"))
