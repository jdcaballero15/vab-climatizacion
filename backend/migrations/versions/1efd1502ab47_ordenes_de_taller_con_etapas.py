"""órdenes de taller con etapas en fila (E06)

Revision ID: 1efd1502ab47
Revises: 22c25d75ac2c
Create Date: 2026-11-03

work_order.workshop_stage: la etapa de taller (retiro, galpón o devolución) en que está
la orden; nula en las de en el lugar (CHECK). work_order_closure.workshop_stage: la etapa
que cerró cada cierre. Las órdenes existentes son todas en el lugar.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1efd1502ab47"
down_revision: str | None = "22c25d75ac2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STAGE = postgresql.ENUM("pickup", "workshop", "delivery", name="workshop_stage")
_CHECK = "ck_work_order_workshop_stage"


def upgrade() -> None:
    _STAGE.create(op.get_bind(), checkfirst=False)
    stage = postgresql.ENUM(name="workshop_stage", create_type=False)
    op.add_column("work_order", sa.Column("workshop_stage", stage, nullable=True))
    op.add_column("work_order_closure", sa.Column("workshop_stage", stage, nullable=True))
    op.create_check_constraint(
        _CHECK, "work_order", "(kind = 'workshop') = (workshop_stage IS NOT NULL)"
    )


def downgrade() -> None:
    op.drop_constraint(_CHECK, "work_order", type_="check")
    op.drop_column("work_order_closure", "workshop_stage")
    op.drop_column("work_order", "workshop_stage")
    _STAGE.drop(op.get_bind(), checkfirst=False)
