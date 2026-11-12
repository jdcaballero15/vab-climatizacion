"""comprobantes PDF de retiro y devolución (E09-01, E09-02)

Revision ID: f2a6d9c3e814
Revises: e5c9f2a8b316
Create Date: 2026-11-10

order_document: el PDF guardado en el bucket, uno por orden y tipo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2a6d9c3e814"
down_revision: str | None = "e5c9f2a8b316"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOCUMENT_KIND = postgresql.ENUM(
    "pickup_receipt", "delivery_receipt", name="document_kind", create_type=False
)


def upgrade() -> None:
    DOCUMENT_KIND.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "order_document",
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("kind", DOCUMENT_KIND, nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["stored_file.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_order_document_kind",
        "order_document",
        ["work_order_id", "kind"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_order_document_kind", table_name="order_document")
    op.drop_table("order_document")
    DOCUMENT_KIND.drop(op.get_bind(), checkfirst=True)
