"""Справочник контактов «Связаться с нами» по регионам

Revision ID: 0026_region_contacts
Revises: 0025_viewer_role_card_fields
Create Date: 2026-08-12

Раньше дефолтные контакты были захардкожены в card.html. По ТЗ у Москвы/МО
свой набор (два телефона + ссылка на страницу контактов), у регионов — свои,
поэтому храним в таблице. Регион «*» — дефолт для всех, у кого своей записи нет.
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0026_region_contacts"
down_revision = "0025_viewer_role_card_fields"
branch_labels = None
depends_on = None

MOSCOW_CONTACTS = [
    {"type": "email", "value": "stdrf@stdrf.ru"},
    {"type": "phone", "value": "+7 (495) 650-28-46"},
    {"type": "phone", "value": "+7 (495) 650-79-71"},
    {"type": "website", "value": "https://stdrf.ru/kontakti/", "label": "www.stdrf.ru"},
]


def upgrade() -> None:
    op.create_table(
        "region_contacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("region", sa.Text(), nullable=False),
        sa.Column("contacts", JSONB(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_region_contacts"),
        sa.UniqueConstraint("region", name="uq_region_contacts_region"),
    )
    payload = json.dumps(MOSCOW_CONTACTS, ensure_ascii=False)
    op.execute(
        sa.text(
            "INSERT INTO region_contacts (region, contacts) "
            "VALUES ('*', CAST(:c AS jsonb)), "
            "('Москва', CAST(:c AS jsonb)), "
            "('Московская область', CAST(:c AS jsonb)) "
            "ON CONFLICT (region) DO NOTHING"
        ).bindparams(c=payload)
    )


def downgrade() -> None:
    op.drop_table("region_contacts")
