"""restablecer la contraseña de un usuario (E01-05)

Revision ID: c5e9a3d7b214
Revises: b3d6f8a1c925
Create Date: 2026-10-28

Marca de contraseña temporal y el último restablecimiento: quién y cuándo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5e9a3d7b214"
down_revision: str | None = "b3d6f8a1c925"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK = "app_user_password_reset_by_fkey"


def upgrade() -> None:
    op.add_column(
        "app_user",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "app_user", sa.Column("password_reset_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("app_user", sa.Column("password_reset_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(_FK, "app_user", "app_user", ["password_reset_by"], ["id"])


def downgrade() -> None:
    op.drop_constraint(_FK, "app_user", type_="foreignkey")
    op.drop_column("app_user", "password_reset_by")
    op.drop_column("app_user", "password_reset_at")
    op.drop_column("app_user", "must_change_password")
