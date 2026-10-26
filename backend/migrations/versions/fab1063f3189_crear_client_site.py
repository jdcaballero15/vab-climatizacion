"""crear client_site y asociar contactos a un domicilio

Revision ID: fab1063f3189
Revises: db29fc2db829
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "fab1063f3189"
down_revision: str | None = "db29fc2db829"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_site",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("reference", sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_site_client_id", "client_site", ["client_id"])
    op.add_column("client_contact", sa.Column("client_site_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "client_contact_client_site_id_fkey",
        "client_contact",
        "client_site",
        ["client_site_id"],
        ["id"],
    )
    op.create_index("ix_client_contact_client_site_id", "client_contact", ["client_site_id"])


def downgrade() -> None:
    op.drop_index("ix_client_contact_client_site_id", table_name="client_contact")
    op.drop_constraint("client_contact_client_site_id_fkey", "client_contact", type_="foreignkey")
    op.drop_column("client_contact", "client_site_id")
    op.drop_index("ix_client_site_client_id", table_name="client_site")
    op.drop_table("client_site")
