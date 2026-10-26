"""agregar canal y solicitante a work_order

Revision ID: b4e1c7a20d93
Revises: 9ded0ea86f52
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4e1c7a20d93"
down_revision: str | None = "9ded0ea86f52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORDER_CHANNEL = postgresql.ENUM(
    "whatsapp", "email", "phone", "in_person", name="order_channel", create_type=False
)


def upgrade() -> None:
    ORDER_CHANNEL.create(op.get_bind())
    # Nulas: las órdenes de mantenimiento (E07-04) no tienen canal. En las manuales lo
    # exige la API.
    op.add_column("work_order", sa.Column("channel", ORDER_CHANNEL, nullable=True))
    op.add_column("work_order", sa.Column("requester_name", sa.String(length=255), nullable=True))
    op.add_column("work_order", sa.Column("requester_area", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("work_order", "requester_area")
    op.drop_column("work_order", "requester_name")
    op.drop_column("work_order", "channel")
    ORDER_CHANNEL.drop(op.get_bind())
