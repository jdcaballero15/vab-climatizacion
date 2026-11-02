"""materiales y su lista de precios (E02-05, E02-06)

Revision ID: 63b8f5e979d4
Revises: a8c2e4f6b013
Create Date: 2026-11-02

part: el catálogo de materiales. part_price: el precio de lista con fecha de vigencia;
nunca se edita una fila, se agrega una nueva y el vigente es el último.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "63b8f5e979d4"
down_revision: str | None = "a8c2e4f6b013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "part",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=20), server_default="unidad", nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_part_name", "part", [sa.literal_column("lower(name)")], unique=True)
    op.create_table(
        "part_price",
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("list_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint("list_price >= 0", name="ck_part_price_list_price"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["app_user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["part_id"],
            ["part.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_part_price_part_id"), "part_price", ["part_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_part_price_part_id"), table_name="part_price")
    op.drop_table("part_price")
    op.drop_index("uq_part_name", table_name="part")
    op.drop_table("part")
