"""crear la referencia a Persat de lo importado (E11-01, E11-02)

Revision ID: d9f1b3a7c520
Revises: c4e8a2f6d915
Create Date: 2026-10-28

Una fila por registro importado: entidad, id en el sistema nuevo e id en Persat.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9f1b3a7c520"
down_revision: str | None = "c4e8a2f6d915"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "legacy_reference",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("legacy_id", sa.String(length=255), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("entity", "source", "legacy_id", name="uq_legacy_reference_entity_id"),
    )
    op.create_index("ix_legacy_reference_entity_id", "legacy_reference", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_legacy_reference_entity_id", table_name="legacy_reference")
    op.drop_table("legacy_reference")
