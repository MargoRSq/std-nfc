"""immutable_unaccent — квалифицировать unaccent схемой (иначе бэкап не восстановить)

Revision ID: 0022_unaccent_schema_qualified
Revises: 0021_slug_allow_dot
Create Date: 2026-07-15

pg_dump восстанавливает дамп с `search_path = ''`. Тело функции ссылалось на
`unaccent($1)` без схемы → при restore функция не создавалась → падала
CREATE TABLE cards (у неё generated-колонка full_name_search на этой функции)
→ дальше сыпался весь дамп: COPY в несуществующую таблицу рассинхронизировал
поток, и строки данных парсились как SQL. Итог: бэкап физически есть, а
восстановить из него БД нельзя.

Схемо-квалифицированное тело чинит restore. На живой базе поведение то же.
"""

from alembic import op

revision = "0022_unaccent_schema_qualified"
down_revision = "0021_slug_allow_dot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
        RETURNS text AS $$
            SELECT public.unaccent('public.unaccent'::regdictionary, $1)
        $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    """)


def downgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.immutable_unaccent(text)
        RETURNS text AS $$
            SELECT unaccent($1)
        $$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    """)
