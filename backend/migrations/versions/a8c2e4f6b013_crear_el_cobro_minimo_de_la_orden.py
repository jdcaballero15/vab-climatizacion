"""importes y estado de cobro de la orden terminada (E04-14, versión mínima)

Revision ID: a8c2e4f6b013
Revises: e7b3c9d1f024
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8c2e4f6b013"
down_revision: str | None = "e7b3c9d1f024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUSES = ("pending", "invoiced")


def upgrade() -> None:
    postgresql.ENUM(*_STATUSES, name="billing_status").create(op.get_bind())

    op.create_table(
        "work_order_billing",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("parts_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("labor_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(*_STATUSES, name="billing_status", create_type=False),
            nullable=False,
        ),
        sa.Column("invoice_number", sa.String(length=50), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "parts_amount >= 0 AND labor_amount >= 0", name="ck_work_order_billing_amounts"
        ),
    )
    op.create_index(
        "uq_work_order_billing_work_order",
        "work_order_billing",
        ["work_order_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_work_order_billing_work_order", table_name="work_order_billing")
    op.drop_table("work_order_billing")
    postgresql.ENUM(name="billing_status").drop(op.get_bind())
