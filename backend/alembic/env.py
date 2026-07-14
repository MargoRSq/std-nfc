import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from std_cards.db.base import metadata as target_metadata
from std_cards.infrastructure.repositories import db_models  # noqa: F401  — register tables

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from std_cards.config import settings  # noqa: E402

database_url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "+psycopg")
if not database_url:
    database_url = settings.effective_migrate_url
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
