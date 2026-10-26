"""crear equipment y prefijo de código por tipo de equipo

Revision ID: 2ecd8961c92f
Revises: fab1063f3189
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2ecd8961c92f"
down_revision: str | None = "fab1063f3189"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Prefijos decididos en D-002 para los tipos iniciales (migración 891a93da0872). Si alguno
# fue renombrado, queda sin prefijo y sus equipos usan "EO".
INITIAL_PREFIXES = {
    "Aire acondicionado": "EA",
    "Cámara de frío": "EC",
    "Heladera comercial": "EH",
    "Heladera familiar": "EH",
    "Freezer": "EF",
    "Otros": "EO",
}


def upgrade() -> None:
    op.add_column("equipment_type", sa.Column("code_prefix", sa.String(length=10), nullable=True))
    for name, prefix in INITIAL_PREFIXES.items():
        op.execute(
            sa.text(
                "UPDATE equipment_type SET code_prefix = :prefix WHERE lower(name) = lower(:name)"
            ).bindparams(prefix=prefix, name=name)
        )

    op.create_table(
        "equipment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_site_id", sa.Uuid(), nullable=False),
        sa.Column("equipment_type_id", sa.Uuid(), nullable=False),
        sa.Column("internal_code", sa.String(length=50), nullable=False),
        sa.Column("location_note", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("serial_number", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["client_site_id"], ["client_site.id"]),
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_type.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("internal_code"),
    )
    op.create_index("ix_equipment_client_site_id", "equipment", ["client_site_id"])
    op.create_index("ix_equipment_equipment_type_id", "equipment", ["equipment_type_id"])


def downgrade() -> None:
    op.drop_index("ix_equipment_equipment_type_id", table_name="equipment")
    op.drop_index("ix_equipment_client_site_id", table_name="equipment")
    op.drop_table("equipment")
    op.drop_column("equipment_type", "code_prefix")
