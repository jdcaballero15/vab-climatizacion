"""firma del cliente en el cierre (E05-07)

Revision ID: d1a4f7c2e958
Revises: c5e9a3d7b214
Create Date: 2026-10-28

Tabla signature (imagen en el bucket y nombre de quien firma, sin DNI por D-008) y el
motivo por el que un cierre no tiene firma (D-011). Los cierres anteriores quedan sin
firma ni motivo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1a4f7c2e958"
down_revision: str | None = "c5e9a3d7b214"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REASONS = ("client_absent", "refused", "other")
_PURPOSES = ("closure", "pickup", "delivery")
_CHECK = "ck_work_order_closure_no_signature_text"


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(*_REASONS, name="no_signature_reason").create(bind)
    postgresql.ENUM(*_PURPOSES, name="signature_purpose").create(bind)

    op.add_column(
        "work_order_closure",
        sa.Column(
            "no_signature_reason",
            postgresql.ENUM(*_REASONS, name="no_signature_reason", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "work_order_closure", sa.Column("no_signature_text", sa.String(length=255), nullable=True)
    )
    op.create_check_constraint(
        _CHECK,
        "work_order_closure",
        "(no_signature_reason IS NOT DISTINCT FROM 'other') = (no_signature_text IS NOT NULL)",
    )

    op.create_table(
        "signature",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("closure_id", sa.Uuid(), nullable=False),
        sa.Column(
            "purpose",
            postgresql.ENUM(*_PURPOSES, name="signature_purpose", create_type=False),
            nullable=False,
        ),
        sa.Column("signer_name", sa.String(length=120), nullable=False),
        sa.Column("image_file_id", sa.Uuid(), nullable=False),
        sa.Column(
            "signed_at",
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
        sa.ForeignKeyConstraint(["closure_id"], ["work_order_closure.id"]),
        sa.ForeignKeyConstraint(["image_file_id"], ["stored_file.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("image_file_id"),
    )
    op.create_index("ix_signature_closure_id", "signature", ["closure_id"])


def downgrade() -> None:
    op.drop_index("ix_signature_closure_id", table_name="signature")
    op.drop_table("signature")
    op.drop_constraint(_CHECK, "work_order_closure", type_="check")
    op.drop_column("work_order_closure", "no_signature_text")
    op.drop_column("work_order_closure", "no_signature_reason")
    bind = op.get_bind()
    postgresql.ENUM(name="signature_purpose").drop(bind)
    postgresql.ENUM(name="no_signature_reason").drop(bind)
