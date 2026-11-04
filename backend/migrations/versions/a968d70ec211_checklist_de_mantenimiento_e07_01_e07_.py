"""checklist de mantenimiento (E07-01, E07-06 y E07-08)

Revision ID: a968d70ec211
Revises: 451cd042f251
Create Date: 2026-11-04

maintenance_check_step: la lista única de pasos que edita la oficina, con los pasos
iniciales. work_order_check_item: la copia de los pasos que se lleva cada orden de
mantenimiento al generarse. work_order_closure_check: OK / No OK de la escuadrilla por
paso, con observación y "requiere reparación".
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a968d70ec211"
down_revision: str | None = "451cd042f251"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Pasos iniciales: el cliente todavía no pasó su checklist real (Gonza, 2026-11-03). Van en
# la migración porque también tienen que existir en producción; la oficina los edita.
INITIAL_STEPS = (
    "Limpieza de filtros",
    "Limpieza de serpentinas (evaporadora y condensadora)",
    "Revisión del drenaje",
    "Control de presiones de gas",
    "Control de conexiones eléctricas y consumo",
    "Prueba de funcionamiento",
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
    step = op.create_table(
        "maintenance_check_step",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_maintenance_check_step_name",
        "maintenance_check_step",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "work_order_check_item",
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["step_id"], ["maintenance_check_step.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_work_order_check_item_work_order_id"), "work_order_check_item", ["work_order_id"]
    )
    op.create_index(
        "uq_work_order_check_item_position",
        "work_order_check_item",
        ["work_order_id", "position"],
        unique=True,
    )
    op.create_table(
        "work_order_closure_check",
        sa.Column("closure_id", sa.Uuid(), nullable=False),
        sa.Column("check_item_id", sa.Uuid(), nullable=False),
        sa.Column("result", sa.Enum("ok", "not_ok", name="check_result"), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("requires_repair", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "(result = 'not_ok') = (observation IS NOT NULL)",
            name="ck_work_order_closure_check_observation",
        ),
        sa.CheckConstraint(
            "result = 'not_ok' OR NOT requires_repair",
            name="ck_work_order_closure_check_repair",
        ),
        sa.ForeignKeyConstraint(["check_item_id"], ["work_order_check_item.id"]),
        sa.ForeignKeyConstraint(["closure_id"], ["work_order_closure.id"]),
        sa.PrimaryKeyConstraint("closure_id", "check_item_id"),
    )
    op.bulk_insert(
        step,
        [
            {"id": uuid.uuid4(), "name": name, "position": position, "is_active": True}
            for position, name in enumerate(INITIAL_STEPS)
        ],
    )
    # Las órdenes de mantenimiento ya generadas y sin cerrar también llevan el checklist.
    op.execute(
        """
        INSERT INTO work_order_check_item (id, work_order_id, step_id, position, name)
        SELECT gen_random_uuid(), o.id, s.id, s.position, s.name
        FROM work_order o CROSS JOIN maintenance_check_step s
        WHERE o.maintenance_plan_id IS NOT NULL
          AND o.status IN ('pending', 'assigned', 'in_progress')
          AND o.kind = 'on_site'
          AND o.deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_table("work_order_closure_check")
    sa.Enum(name="check_result").drop(op.get_bind(), checkfirst=True)
    op.drop_index("uq_work_order_check_item_position", table_name="work_order_check_item")
    op.drop_index(
        op.f("ix_work_order_check_item_work_order_id"), table_name="work_order_check_item"
    )
    op.drop_table("work_order_check_item")
    op.drop_index("uq_maintenance_check_step_name", table_name="maintenance_check_step")
    op.drop_table("maintenance_check_step")
