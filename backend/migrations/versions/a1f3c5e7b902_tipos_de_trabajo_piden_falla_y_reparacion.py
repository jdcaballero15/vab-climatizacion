"""tipos de trabajo que piden falla y reparación al cerrar (E02-10)

Revision ID: a1f3c5e7b902
Revises: e5b8c1d4a903
Create Date: 2026-10-26

Marca por nombre los tipos iniciales donde falla y reparación tienen sentido. Si alguno
fue renombrado, queda sin marcar y se marca desde la pantalla.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f3c5e7b902"
down_revision: str | None = "e5b8c1d4a903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_WITH_FAILURE_REPAIR = ("reparación", "service")


def upgrade() -> None:
    op.add_column(
        "work_type",
        sa.Column(
            "requires_failure_repair",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.get_bind().execute(
        sa.text(
            "UPDATE work_type SET requires_failure_repair = true WHERE lower(name) IN :names"
        ).bindparams(sa.bindparam("names", expanding=True)),
        {"names": list(_WITH_FAILURE_REPAIR)},
    )


def downgrade() -> None:
    op.drop_column("work_type", "requires_failure_repair")
