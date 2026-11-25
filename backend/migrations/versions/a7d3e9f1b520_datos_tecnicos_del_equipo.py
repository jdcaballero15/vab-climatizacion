"""datos técnicos del equipo: frigorías, gas y alimentación (E03-10)

Revision ID: a7d3e9f1b520
Revises: f2a6d9c3e814
Create Date: 2026-11-25

Tres columnas nulas en equipment; los valores válidos los controla la API.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7d3e9f1b520"
down_revision: str | None = "f2a6d9c3e814"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("equipment", sa.Column("capacity_frigorias", sa.Integer(), nullable=True))
    op.add_column("equipment", sa.Column("refrigerant", sa.String(length=20), nullable=True))
    op.add_column("equipment", sa.Column("power_supply", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("equipment", "power_supply")
    op.drop_column("equipment", "refrigerant")
    op.drop_column("equipment", "capacity_frigorias")
