"""intentos de ingreso fallidos (E01-06)

Revision ID: a1c3e5f7b902
Revises: c7e2a4f8d913
Create Date: 2026-11-10

login_failure: cada intento fallido, por correo y dirección IP, para bloquear la cuenta
tras varios seguidos.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c3e5f7b902"
down_revision: str | None = "c7e2a4f8d913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_failure",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
    op.create_index("ix_login_failure_email_at", "login_failure", ["email", "occurred_at"])
    op.create_index("ix_login_failure_ip_at", "login_failure", ["ip", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_login_failure_ip_at", table_name="login_failure")
    op.drop_index("ix_login_failure_email_at", table_name="login_failure")
    op.drop_table("login_failure")
