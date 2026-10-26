"""crear failure

Revision ID: 4094833fa904
Revises: 891a93da0872
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4094833fa904"
down_revision: str | None = "891a93da0872"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Crea la tabla vacía. La lista inicial del cliente se carga en 7a8a9559f9b4.


def upgrade() -> None:
    op.create_table(
        "failure",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipment_type_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["equipment_type_id"], ["equipment_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_failure_equipment_type_id"), "failure", ["equipment_type_id"], unique=False
    )
    op.create_index(
        "uq_failure_scope_name",
        "failure",
        [
            sa.text("coalesce(equipment_type_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            sa.text("lower(name)"),
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_failure_scope_name", table_name="failure")
    op.drop_index(op.f("ix_failure_equipment_type_id"), table_name="failure")
    op.drop_table("failure")
