"""planes de mantenimiento (E07-03 y E07-04)

Revision ID: 451cd042f251
Revises: 1efd1502ab47
Create Date: 2026-11-03

maintenance_plan: el plan de un equipo abonado (cada cuántos meses, próxima visita,
escuadrilla que suele ir y fin del abono). work_order.maintenance_plan_id y
maintenance_due_on: la visita que generó la orden; el índice único evita duplicarla.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "451cd042f251"
down_revision: str | None = "1efd1502ab47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK = "fk_work_order_maintenance_plan_id"
_CHECK = "ck_work_order_maintenance_due"


def upgrade() -> None:
    op.create_table(
        "maintenance_plan",
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("work_type_id", sa.Uuid(), nullable=False),
        sa.Column("crew_id", sa.Uuid(), nullable=True),
        sa.Column("every_months", sa.Integer(), nullable=False),
        sa.Column("next_due_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.CheckConstraint("every_months BETWEEN 1 AND 24", name="ck_maintenance_plan_every"),
        sa.ForeignKeyConstraint(["crew_id"], ["crew.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["work_type_id"], ["work_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_maintenance_plan_equipment_id"), "maintenance_plan", ["equipment_id"])
    op.create_index(
        "uq_maintenance_plan_open_equipment",
        "maintenance_plan",
        ["equipment_id"],
        unique=True,
        postgresql_where=sa.text("ends_on IS NULL AND deleted_at IS NULL"),
    )
    op.add_column("work_order", sa.Column("maintenance_plan_id", sa.Uuid(), nullable=True))
    op.add_column("work_order", sa.Column("maintenance_due_on", sa.Date(), nullable=True))
    op.create_foreign_key(_FK, "work_order", "maintenance_plan", ["maintenance_plan_id"], ["id"])
    op.create_check_constraint(
        _CHECK, "work_order", "(maintenance_plan_id IS NULL) = (maintenance_due_on IS NULL)"
    )
    op.create_index(
        "uq_work_order_maintenance_visit",
        "work_order",
        ["maintenance_plan_id", "maintenance_due_on"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_work_order_maintenance_visit", table_name="work_order")
    op.drop_constraint(_CHECK, "work_order", type_="check")
    op.drop_constraint(_FK, "work_order", type_="foreignkey")
    op.drop_column("work_order", "maintenance_due_on")
    op.drop_column("work_order", "maintenance_plan_id")
    op.drop_index(
        "uq_maintenance_plan_open_equipment",
        table_name="maintenance_plan",
        postgresql_where=sa.text("ends_on IS NULL AND deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_maintenance_plan_equipment_id"), table_name="maintenance_plan")
    op.drop_table("maintenance_plan")
