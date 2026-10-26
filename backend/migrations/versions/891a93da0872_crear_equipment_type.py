"""crear equipment_type con los tipos de equipo iniciales

Revision ID: 891a93da0872
Revises: 51d29e6b730e
Create Date: 2026-10-26

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "891a93da0872"
down_revision: str | None = "51d29e6b730e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lista inicial que pasó el cliente. Va en la migración y no en make seed porque
# también tiene que existir en producción (E02-02, criterio 6). Siguen editables.
INITIAL_EQUIPMENT_TYPES = (
    "Aire acondicionado",
    "Cámara de frío",
    "Heladera comercial",
    "Heladera familiar",
    "Freezer",
    "Otros",
)


def upgrade() -> None:
    equipment_type = op.create_table(
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

    op.bulk_insert(
        equipment_type,
        [{"id": uuid.uuid4(), "name": name, "is_active": True} for name in INITIAL_EQUIPMENT_TYPES],
    )


def downgrade() -> None:
    op.drop_index("uq_equipment_type_name", table_name="equipment_type")
    op.drop_table("equipment_type")
