"""crear work_order_closure_photo: fotos del cierre (E05-06)

Revision ID: f4b8d2a6c731
Revises: e2a7c9d4f816
Create Date: 2026-10-28

Hasta 5 fotos por cierre, en orden. Cada archivo del bucket es foto de un solo cierre.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4b8d2a6c731"
down_revision: str | None = "e2a7c9d4f816"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_order_closure_photo",
        sa.Column("closure_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["closure_id"], ["work_order_closure.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["stored_file.id"]),
        sa.PrimaryKeyConstraint("closure_id", "file_id"),
        sa.UniqueConstraint("file_id"),
    )


def downgrade() -> None:
    op.drop_table("work_order_closure_photo")
