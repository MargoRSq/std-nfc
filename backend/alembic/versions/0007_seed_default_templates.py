"""seed default templates for each category

Revision ID: 0007_seed_default_templates
Revises: 0006_feedback_messages
Create Date: 2026-05-02

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_seed_default_templates"
down_revision: str | None = "0006_feedback_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO templates (name, category_id, default_fields, default_styles, custom_field_schema, created_by)
        SELECT
            t.name,
            c.id,
            t.default_fields::jsonb,
            t.default_styles::jsonb,
            '[]'::jsonb,
            NULL
        FROM (VALUES
            (
                'Платиновые',
                'platinum',
                '{}',
                '{"bg_kind": "solid", "bg_color": "#2A3F60", "photo_shape": "square"}'
            ),
            (
                'Золотые',
                'gold',
                '{}',
                '{"bg_kind": "solid", "bg_color": "#FFFFFF", "photo_shape": "square"}'
            ),
            (
                'Серебряные',
                'silver',
                '{}',
                '{"bg_kind": "solid", "bg_color": "#FFFFFF", "photo_shape": "square"}'
            ),
            (
                'По умолчанию',
                'bronze',
                '{}',
                '{"bg_kind": "gradient", "bg_gradient": {"start": "#1F1E5E", "end": "#798BFF", "angle": 180}, "photo_shape": "circle"}'
            )
        ) AS t(name, code, default_fields, default_styles)
        JOIN categories c ON c.code = t.code
        ON CONFLICT (name, category_id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM templates
        WHERE name IN ('Платиновые', 'Золотые', 'Серебряные', 'По умолчанию', 'Бронзовые')
    """)
