"""baja de clientes y equipos, unificación y traslados (E03-07, E03-08, E03-09, E12-02)

Revision ID: c7e2a4f8d913
Revises: a968d70ec211
Create Date: 2026-11-10

audit_event: quién dio de baja, restauró o unificó (base de la auditoría de E12-01).
client.merged_into_id: en qué cliente se unificó uno dado de baja. equipment_transfer: el
paso de un equipo a otro cliente, con el código anterior.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7e2a4f8d913"
down_revision: str | None = "a968d70ec211"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "audit_event",
        sa.Column("entity", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("detail", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["actor_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_event_entity_id"), "audit_event", ["entity_id"])
    op.add_column("client", sa.Column("merged_into_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "client_merged_into_id_fkey", "client", "client", ["merged_into_id"], ["id"]
    )
    op.create_table(
        "equipment_transfer",
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("from_client_id", sa.Uuid(), nullable=False),
        sa.Column("from_site_id", sa.Uuid(), nullable=False),
        sa.Column("from_code", sa.String(length=50), nullable=False),
        sa.Column("to_client_id", sa.Uuid(), nullable=False),
        sa.Column("to_site_id", sa.Uuid(), nullable=False),
        sa.Column("to_code", sa.String(length=50), nullable=False),
        sa.Column("transferred_by", sa.Uuid(), nullable=False),
        sa.Column(
            "transferred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["from_client_id"], ["client.id"]),
        sa.ForeignKeyConstraint(["from_site_id"], ["client_site.id"]),
        sa.ForeignKeyConstraint(["to_client_id"], ["client.id"]),
        sa.ForeignKeyConstraint(["to_site_id"], ["client_site.id"]),
        sa.ForeignKeyConstraint(["transferred_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_equipment_transfer_equipment_id"), "equipment_transfer", ["equipment_id"]
    )
    op.create_index(op.f("ix_equipment_transfer_from_code"), "equipment_transfer", ["from_code"])


def downgrade() -> None:
    op.drop_index(op.f("ix_equipment_transfer_from_code"), table_name="equipment_transfer")
    op.drop_index(op.f("ix_equipment_transfer_equipment_id"), table_name="equipment_transfer")
    op.drop_table("equipment_transfer")
    op.drop_constraint("client_merged_into_id_fkey", "client", type_="foreignkey")
    op.drop_column("client", "merged_into_id")
    op.drop_index(op.f("ix_audit_event_entity_id"), table_name="audit_event")
    op.drop_table("audit_event")
