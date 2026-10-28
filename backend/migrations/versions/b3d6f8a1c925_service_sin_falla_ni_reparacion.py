"""el service no pide falla y reparación al cerrar (E02-10)

Revision ID: b3d6f8a1c925
Revises: f4b8d2a6c731
Create Date: 2026-10-28

El cliente confirmó que en el service no suele haber falla: si aparece, se anota en la
observación del cierre. Desmarca por nombre; si fue renombrado, no toca nada.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3d6f8a1c925"
down_revision: str | None = "f4b8d2a6c731"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _set_service(value: bool) -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE work_type SET requires_failure_repair = :value WHERE lower(name) = 'service'"
        ),
        {"value": value},
    )


def upgrade() -> None:
    _set_service(False)


def downgrade() -> None:
    _set_service(True)
