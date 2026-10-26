"""asignar órdenes a escuadrillas: work_order_assignment.technician_id pasa a crew_id

Revision ID: e5b8c1d4a903
Revises: d3a9b6e2f417
Create Date: 2026-10-26

D-013: las órdenes se asignan a una escuadrilla, no a un técnico. No hay forma de
saber a qué escuadrilla correspondía cada técnico, así que la migración solo corre con
la tabla vacía (en producción todavía no hay asignaciones). Si encuentra filas, falla
sin tocar nada: no se borra nada en silencio.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5b8c1d4a903"
down_revision: str | None = "d3a9b6e2f417"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _require_empty() -> None:
    count = op.get_bind().scalar(sa.text("SELECT count(*) FROM work_order_assignment"))
    if count:
        raise RuntimeError(
            f"work_order_assignment tiene {count} asignaciones y no se pueden convertir "
            "entre técnico y escuadrilla. En una base de prueba, bajala con "
            "'alembic downgrade b4e1c7a20d93' (quita la tabla) y volvé a subir."
        )


def upgrade() -> None:
    _require_empty()
    op.drop_index("ix_work_order_assignment_technician_id", table_name="work_order_assignment")
    op.drop_column("work_order_assignment", "technician_id")
    op.add_column("work_order_assignment", sa.Column("crew_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        "work_order_assignment_crew_id_fkey",
        "work_order_assignment",
        "crew",
        ["crew_id"],
        ["id"],
    )
    op.create_index("ix_work_order_assignment_crew_id", "work_order_assignment", ["crew_id"])


def downgrade() -> None:
    _require_empty()
    op.drop_index("ix_work_order_assignment_crew_id", table_name="work_order_assignment")
    op.drop_constraint(
        "work_order_assignment_crew_id_fkey", "work_order_assignment", type_="foreignkey"
    )
    op.drop_column("work_order_assignment", "crew_id")
    op.add_column("work_order_assignment", sa.Column("technician_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        "work_order_assignment_technician_id_fkey",
        "work_order_assignment",
        "app_user",
        ["technician_id"],
        ["id"],
    )
    op.create_index(
        "ix_work_order_assignment_technician_id", "work_order_assignment", ["technician_id"]
    )
