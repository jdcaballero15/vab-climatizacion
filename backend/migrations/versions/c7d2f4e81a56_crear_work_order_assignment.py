"""crear work_order_assignment y agregar requires_approval a work_order

Revision ID: c7d2f4e81a56
Revises: b4e1c7a20d93
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d2f4e81a56"
down_revision: str | None = "b4e1c7a20d93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "work_order",
        sa.Column(
            "requires_approval",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_table(
        "work_order_assignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("technician_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["technician_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_work_order_assignment_work_order_id", "work_order_assignment", ["work_order_id"]
    )
    op.create_index(
        "ix_work_order_assignment_technician_id", "work_order_assignment", ["technician_id"]
    )
    # Una sola asignación vigente por orden: un solo técnico responsable (R7).
    op.create_index(
        "uq_work_order_assignment_current",
        "work_order_assignment",
        ["work_order_id"],
        unique=True,
        postgresql_where=sa.text("unassigned_at IS NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_work_order_assignment_current", table_name="work_order_assignment")
    op.drop_index("ix_work_order_assignment_technician_id", table_name="work_order_assignment")
    op.drop_index("ix_work_order_assignment_work_order_id", table_name="work_order_assignment")
    op.drop_table("work_order_assignment")
    op.drop_column("work_order", "requires_approval")
