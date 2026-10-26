"""crear equipment_type

Revision ID: 891a93da0872
Revises: 51d29e6b730e
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "891a93da0872"
down_revision: str | None = "51d29e6b730e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Sin tipos iniciales: la lista la tiene que pasar el cliente (E02-02, criterio 6).


def upgrade() -> None:
    op.create_table(
        "equipment_type",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_equipment_type_name", "equipment_type", [sa.text("lower(name)")], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_equipment_type_name", table_name="equipment_type")
    op.drop_table("equipment_type")
