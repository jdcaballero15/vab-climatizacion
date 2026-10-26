"""agregar failure_id a repair

Revision ID: 154f870b70dc
Revises: 11cec86d9eaa
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "154f870b70dc"
down_revision: str | None = "11cec86d9eaa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Cada reparación pertenece a una falla (E02-04). La tabla todavía no tiene datos en ningún
# entorno, así que la columna nace obligatoria sin valor por defecto.


def upgrade() -> None:
    op.add_column("repair", sa.Column("failure_id", sa.Uuid(), nullable=False))
    op.create_foreign_key("repair_failure_id_fkey", "repair", "failure", ["failure_id"], ["id"])
    op.create_index(op.f("ix_repair_failure_id"), "repair", ["failure_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_repair_failure_id"), table_name="repair")
    op.drop_constraint("repair_failure_id_fkey", "repair", type_="foreignkey")
    op.drop_column("repair", "failure_id")
