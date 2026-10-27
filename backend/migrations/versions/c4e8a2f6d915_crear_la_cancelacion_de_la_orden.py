"""crear la cancelación de la orden (E04-07)

Revision ID: c4e8a2f6d915
Revises: b7d2e9f4c613
Create Date: 2026-10-27

Motivo de una lista fija (más "Otro" con texto), quién canceló y cuándo. Una por orden.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4e8a2f6d915"
down_revision: str | None = "b7d2e9f4c613"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REASONS = ("entered_by_mistake", "duplicate", "client_cancelled", "other")


def upgrade() -> None:
    postgresql.ENUM(*_REASONS, name="cancel_reason").create(op.get_bind())

    op.create_table(
        "work_order_cancellation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column(
            "reason",
            postgresql.ENUM(*_REASONS, name="cancel_reason", create_type=False),
            nullable=False,
        ),
        sa.Column("reason_text", sa.String(length=255), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=False),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["cancelled_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(reason = 'other') = (reason_text IS NOT NULL)",
            name="ck_work_order_cancellation_reason_text",
        ),
    )
    op.create_index(
        "uq_work_order_cancellation_work_order",
        "work_order_cancellation",
        ["work_order_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_work_order_cancellation_work_order", table_name="work_order_cancellation")
    op.drop_table("work_order_cancellation")
    postgresql.ENUM(name="cancel_reason").drop(op.get_bind())
