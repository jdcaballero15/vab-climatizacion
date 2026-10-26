"""crear client y client_contact

Revision ID: db29fc2db829
Revises: 7a8a9559f9b4
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "db29fc2db829"
down_revision: str | None = "7a8a9559f9b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

client_segment = sa.Enum(
    "private_person",
    "business",
    "government",
    "healthcare",
    "hotel",
    "unclassified",
    name="client_segment",
)
tax_condition = sa.Enum(
    "final_consumer", "registered_taxpayer", "monotributo", name="tax_condition"
)


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "client",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("segment", client_segment, nullable=False),
        sa.Column("tax_id", sa.String(length=20), nullable=True),
        sa.Column("tax_condition", tax_condition, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
    )
    op.create_table(
        "client_contact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("receives_monthly_report", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_contact_client_id", "client_contact", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_client_contact_client_id", table_name="client_contact")
    op.drop_table("client_contact")
    op.drop_table("client")
    # drop_table no borra los tipos enum de Postgres.
    tax_condition.drop(op.get_bind())
    client_segment.drop(op.get_bind())
