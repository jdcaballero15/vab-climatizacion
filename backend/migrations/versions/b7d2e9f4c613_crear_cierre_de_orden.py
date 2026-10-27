"""crear el cierre de la orden (E05-04, E05-08, E05-12)

Revision ID: b7d2e9f4c613
Revises: a1f3c5e7b902
Create Date: 2026-10-26

Cierre básico: resultado, falla y reparación (o "Otro"), cómo quedó el equipo, motivo
si no se pudo hacer, observación y clave de idempotencia. Quiénes fueron y las tareas
tildadas van en tablas aparte. Repuestos, fotos y firma llegan en otras historias.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d2e9f4c613"
down_revision: str | None = "a1f3c5e7b902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUMS = {
    "closure_outcome": ("done", "needs_pickup", "needs_revisit", "not_done"),
    "equipment_condition": ("working", "working_with_notes", "not_working"),
    "not_done_reason": ("client_absent", "missing_part", "beyond_repair"),
}


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*_ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in _ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind)

    op.create_table(
        "work_order_closure",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("closed_by", sa.Uuid(), nullable=False),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("outcome", _enum("closure_outcome"), nullable=False),
        sa.Column("failure_id", sa.Uuid(), nullable=True),
        sa.Column("failure_other_text", sa.String(length=255), nullable=True),
        sa.Column("repair_id", sa.Uuid(), nullable=True),
        sa.Column("repair_other_text", sa.String(length=255), nullable=True),
        sa.Column("equipment_condition", _enum("equipment_condition"), nullable=True),
        sa.Column("not_done_reason", _enum("not_done_reason"), nullable=True),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["closed_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["failure_id"], ["failure.id"]),
        sa.ForeignKeyConstraint(["repair_id"], ["repair.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_work_order_closure_work_order_id", "work_order_closure", ["work_order_id"])

    op.create_table(
        "work_order_closure_technician",
        sa.Column("closure_id", sa.Uuid(), nullable=False),
        sa.Column("field_technician_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["closure_id"], ["work_order_closure.id"]),
        sa.ForeignKeyConstraint(["field_technician_id"], ["field_technician.id"]),
        sa.PrimaryKeyConstraint("closure_id", "field_technician_id"),
    )
    op.create_table(
        "work_order_closure_task",
        sa.Column("closure_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["closure_id"], ["work_order_closure.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"]),
        sa.PrimaryKeyConstraint("closure_id", "task_id"),
    )


def downgrade() -> None:
    op.drop_table("work_order_closure_task")
    op.drop_table("work_order_closure_technician")
    op.drop_index("ix_work_order_closure_work_order_id", table_name="work_order_closure")
    op.drop_table("work_order_closure")
    bind = op.get_bind()
    for name in reversed(_ENUMS):
        postgresql.ENUM(name=name).drop(bind)
