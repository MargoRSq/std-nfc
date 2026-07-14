"""cards.public_slug — разрешить точку внутри slug

Revision ID: 0021_slug_allow_dot
Revises: 0020_user_name
Create Date: 2026-07-14

Имена констрейнтов задаём явным SQL: naming_convention добавляет префикс
`ck_<table>_` к constraint_name, и op.drop_constraint("ck_cards_...") получил бы
`ck_cards_ck_cards_...`.
"""

from alembic import op

revision = "0021_slug_allow_dot"
down_revision = "0020_user_name"
branch_labels = None
depends_on = None

NEW_CHECK = (
    r"public_slug ~ '^[A-Za-z0-9_-][A-Za-z0-9_.-]{4,30}[A-Za-z0-9_-]$' "
    r"AND public_slug !~ '\.\.'"
)
OLD_CHECK = r"public_slug ~ '^[A-Za-z0-9_-]{6,32}$'"


def upgrade() -> None:
    op.execute("ALTER TABLE cards DROP CONSTRAINT IF EXISTS ck_cards_public_slug_format")
    op.execute(f"ALTER TABLE cards ADD CONSTRAINT ck_cards_public_slug_format CHECK ({NEW_CHECK})")


def downgrade() -> None:
    op.execute("ALTER TABLE cards DROP CONSTRAINT IF EXISTS ck_cards_public_slug_format")
    op.execute(f"ALTER TABLE cards ADD CONSTRAINT ck_cards_public_slug_format CHECK ({OLD_CHECK})")
