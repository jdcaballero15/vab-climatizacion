"""stock por movimientos: depósitos, camionetas y movimientos (E08-01 a E08-08)

Revision ID: d4b8e1c6a207
Revises: c4e6a8b0d215
Create Date: 2026-11-10

stock_location: depósitos y camionetas (cada camioneta con su escuadrilla). stock_movement:
ingresos, transferencias, usos de los cierres y ajustes; el saldo es la suma (regla 6).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4b8e1c6a207"
down_revision: str | None = "c4e6a8b0d215"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LOCATION_KIND = postgresql.ENUM("warehouse", "truck", name="stock_location_kind", create_type=False)
MOVEMENT_KIND = postgresql.ENUM(
    "receipt", "transfer", "usage", "adjustment", name="stock_movement_kind", create_type=False
)


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    LOCATION_KIND.create(op.get_bind(), checkfirst=True)
    MOVEMENT_KIND.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "stock_location",
        sa.Column("kind", LOCATION_KIND, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("crew_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "kind = 'truck' OR crew_id IS NULL", name="ck_stock_location_crew_only_truck"
        ),
        sa.ForeignKeyConstraint(["crew_id"], ["crew.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_stock_location_crew",
        "stock_location",
        ["crew_id"],
        unique=True,
        postgresql_where=sa.text("crew_id IS NOT NULL AND is_active AND deleted_at IS NULL"),
    )
    op.create_table(
        "stock_movement",
        sa.Column("kind", MOVEMENT_KIND, nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("from_location_id", sa.Uuid(), nullable=True),
        sa.Column("to_location_id", sa.Uuid(), nullable=True),
        sa.Column("work_order_id", sa.Uuid(), nullable=True),
        sa.Column("part_usage_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint("quantity > 0", name="ck_stock_movement_quantity"),
        sa.CheckConstraint(
            "from_location_id IS NOT NULL OR to_location_id IS NOT NULL",
            name="ck_stock_movement_location",
        ),
        sa.CheckConstraint(
            "kind <> 'adjustment' OR reason IS NOT NULL", name="ck_stock_movement_reason"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["from_location_id"], ["stock_location.id"]),
        sa.ForeignKeyConstraint(["part_id"], ["part.id"]),
        sa.ForeignKeyConstraint(["part_usage_id"], ["part_usage.id"]),
        sa.ForeignKeyConstraint(["to_location_id"], ["stock_location.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("part_id", "from_location_id", "to_location_id"):
        op.create_index(op.f(f"ix_stock_movement_{column}"), "stock_movement", [column])
    op.create_index(
        "uq_stock_movement_part_usage",
        "stock_movement",
        ["part_usage_id"],
        unique=True,
        postgresql_where=sa.text("part_usage_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_stock_movement_part_usage", table_name="stock_movement")
    for column in ("part_id", "from_location_id", "to_location_id"):
        op.drop_index(op.f(f"ix_stock_movement_{column}"), table_name="stock_movement")
    op.drop_table("stock_movement")
    op.drop_index("uq_stock_location_crew", table_name="stock_location")
    op.drop_table("stock_location")
    MOVEMENT_KIND.drop(op.get_bind(), checkfirst=True)
    LOCATION_KIND.drop(op.get_bind(), checkfirst=True)
