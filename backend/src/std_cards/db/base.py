from typing import Any

import sqlalchemy as sa

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)


def StdCardsTable(  # noqa: N802
    name: str,
    metadata: sa.MetaData,
    *columns: Any,
    add_timestamps: bool = True,
    add_timestamp_indexes: bool = True,
    **kwargs: Any,
) -> sa.Table:
    """Фабрика таблиц с дефолтными created_at/updated_at + индексами на них.

    Все таблицы в std-cards создаются через эту функцию для единообразия.
    Для партиционированных таблиц (scan_events) — передавай `add_timestamp_indexes=False`,
    индексы создавай явно per-partition.
    """
    extra_columns: list[Any] = []
    extra_constraints: list[Any] = []

    if add_timestamps:
        extra_columns.extend(
            [
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                    doc="Время создания записи",
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                    onupdate=sa.func.now(),
                    doc="Время последнего обновления записи",
                ),
            ]
        )

    if add_timestamps and add_timestamp_indexes:
        extra_constraints.extend(
            [
                sa.Index(f"{name}_created_at_idx", "created_at"),
                sa.Index(f"{name}_updated_at_idx", "updated_at"),
            ]
        )

    indexes_kw = list(kwargs.pop("indexes", []))
    constraints_kw = list(kwargs.pop("constraints", []))

    return sa.Table(
        name,
        metadata,
        *columns,
        *extra_columns,
        *indexes_kw,
        *extra_constraints,
        *constraints_kw,
        **kwargs,
    )
