"""crear stored_file para los archivos del bucket (E00-09)

Revision ID: e2a7c9d4f816
Revises: d9f1b3a7c520
Create Date: 2026-10-28

Solo la referencia al objeto del bucket: clave, tipo, tamaño, quién lo subió y si se confirmó.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2a7c9d4f816"
down_revision: str | None = "d9f1b3a7c520"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stored_file",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["uploaded_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_stored_file_uploaded_by", "stored_file", ["uploaded_by"])


def downgrade() -> None:
    op.drop_index("ix_stored_file_uploaded_by", table_name="stored_file")
    op.drop_table("stored_file")
