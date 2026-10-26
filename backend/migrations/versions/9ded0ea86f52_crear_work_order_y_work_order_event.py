"""crear work_order y work_order_event (máquina de estados de la orden)

Revision ID: 9ded0ea86f52
Revises: 2ecd8961c92f
Create Date: 2026-10-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9ded0ea86f52"
down_revision: str | None = "2ecd8961c92f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Valores congelados al momento de la migración: no se importan del dominio para que
# la migración no cambie si después se suman estados o tipos de evento.
ORDER_STATUS = postgresql.ENUM(
    "pending",
    "assigned",
    "in_progress",
    "done",
    "invoiced",
    "paid",
    "cancelled",
    name="order_status",
    create_type=False,
)
ORDER_KIND = postgresql.ENUM("on_site", "workshop", name="order_kind", create_type=False)
ORDER_SOURCE = postgresql.ENUM("manual", "maintenance", name="order_source", create_type=False)
EVENT_TYPES = (
    "created",
    "status_change",
    "assigned",
    "unassigned",
    "reassigned",
    "review_approved",
    "review_returned",
    "converted_to_workshop",
)


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
    bind = op.get_bind()
    for enum_type in (ORDER_STATUS, ORDER_KIND, ORDER_SOURCE):
        enum_type.create(bind)
    op.execute(sa.schema.CreateSequence(sa.Sequence("work_order_number_seq")))

    op.create_table(
        "work_order",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "number",
            sa.BigInteger(),
            server_default=sa.text("nextval('work_order_number_seq')"),
            nullable=False,
        ),
        sa.Column("kind", ORDER_KIND, nullable=False),
        sa.Column("source", ORDER_SOURCE, nullable=False),
        sa.Column("status", ORDER_STATUS, nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("client_site_id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=True),
        sa.Column("work_type_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.ForeignKeyConstraint(["client_site_id"], ["client_site.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
        sa.ForeignKeyConstraint(["work_type_id"], ["work_type.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
    )
    op.execute("ALTER SEQUENCE work_order_number_seq OWNED BY work_order.number")
    op.create_index("ix_work_order_status", "work_order", ["status"])
    op.create_index("ix_work_order_client_id", "work_order", ["client_id"])
    op.create_index("ix_work_order_client_site_id", "work_order", ["client_site_id"])
    op.create_index("ix_work_order_equipment_id", "work_order", ["equipment_id"])

    op.create_table(
        "work_order_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("from_status", ORDER_STATUS, nullable=True),
        sa.Column("to_status", ORDER_STATUS, nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "event_type IN ({})".format(", ".join(f"'{t}'" for t in EVENT_TYPES)),
            name="ck_work_order_event_type",
        ),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.ForeignKeyConstraint(["actor_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_order_event_work_order_id", "work_order_event", ["work_order_id"])


def downgrade() -> None:
    op.drop_index("ix_work_order_event_work_order_id", table_name="work_order_event")
    op.drop_table("work_order_event")
    op.drop_index("ix_work_order_equipment_id", table_name="work_order")
    op.drop_index("ix_work_order_client_site_id", table_name="work_order")
    op.drop_index("ix_work_order_client_id", table_name="work_order")
    op.drop_index("ix_work_order_status", table_name="work_order")
    # La secuencia es de work_order.number (OWNED BY): se borra junto con la tabla.
    op.drop_table("work_order")
    op.execute("DROP SEQUENCE IF EXISTS work_order_number_seq")
    bind = op.get_bind()
    for enum_type in (ORDER_SOURCE, ORDER_KIND, ORDER_STATUS):
        enum_type.drop(bind)
