"""lotes de importación e historial de Persat (E11-03, E11-05)

Revision ID: e5c9f2a8b316
Revises: d4b8e1c6a207
Create Date: 2026-11-10

import_batch: cada importación confirmada, para deshacerla entera. legacy_reference
suma el lote y su unicidad pasa a ignorar las referencias de lotes deshechos. Las órdenes
importadas de Persat llevan source = persat.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5c9f2a8b316"
down_revision: str | None = "d4b8e1c6a207"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_batch",
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("run_by", sa.String(length=255), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
    op.add_column("legacy_reference", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "legacy_reference_batch_id_fkey", "legacy_reference", "import_batch", ["batch_id"], ["id"]
    )
    op.create_index(op.f("ix_legacy_reference_batch_id"), "legacy_reference", ["batch_id"])
    op.drop_constraint("uq_legacy_reference_entity_id", "legacy_reference", type_="unique")
    op.create_index(
        "uq_legacy_reference_entity_id",
        "legacy_reference",
        ["entity", "source", "legacy_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE order_source ADD VALUE IF NOT EXISTS 'persat'")


def downgrade() -> None:
    # Postgres no saca valores de un enum: se rearma el tipo sin 'persat'. Las órdenes
    # importadas se dan de baja antes, porque el tipo viejo no las puede representar.
    op.execute(
        "UPDATE work_order SET deleted_at = now(), source = 'manual' WHERE source = 'persat'"
    )
    op.execute("ALTER TYPE order_source RENAME TO order_source_old")
    op.execute("CREATE TYPE order_source AS ENUM ('manual', 'maintenance')")
    op.execute(
        "ALTER TABLE work_order ALTER COLUMN source TYPE order_source "
        "USING source::text::order_source"
    )
    op.execute("DROP TYPE order_source_old")
    op.drop_index("uq_legacy_reference_entity_id", table_name="legacy_reference")
    op.create_unique_constraint(
        "uq_legacy_reference_entity_id", "legacy_reference", ["entity", "source", "legacy_id"]
    )
    op.drop_index(op.f("ix_legacy_reference_batch_id"), table_name="legacy_reference")
    op.drop_constraint("legacy_reference_batch_id_fkey", "legacy_reference", type_="foreignkey")
    op.drop_column("legacy_reference", "batch_id")
    op.drop_table("import_batch")
