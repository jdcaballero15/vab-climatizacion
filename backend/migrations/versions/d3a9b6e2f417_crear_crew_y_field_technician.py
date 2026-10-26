"""crear crew y field_technician (escuadrillas y técnicos, D-013)

Revision ID: d3a9b6e2f417
Revises: c7d2f4e81a56
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3a9b6e2f417"
down_revision: str | None = "c7d2f4e81a56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "crew",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("app_user_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["app_user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("app_user_id"),
    )
    op.create_index("uq_crew_name", "crew", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "field_technician",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_field_technician_full_name",
        "field_technician",
        [sa.text("lower(full_name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_field_technician_full_name", table_name="field_technician")
    op.drop_table("field_technician")
    op.drop_index("uq_crew_name", table_name="crew")
    op.drop_table("crew")
