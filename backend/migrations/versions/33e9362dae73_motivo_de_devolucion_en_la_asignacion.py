"""motivo de devolución en la asignación (E04-08, criterio 3)

Revision ID: 33e9362dae73
Revises: 0cf779285368
Create Date: 2026-11-03

work_order_assignment.return_reason: por qué administración devolvió una orden Terminada
a la escuadrilla. Nulo en las asignaciones comunes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "33e9362dae73"
down_revision: str | None = "0cf779285368"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("work_order_assignment", sa.Column("return_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("work_order_assignment", "return_reason")
