"""factura, cobro y otros cargos de la orden (E04-09, E04-10, E04-11 y E04-13)

Revision ID: b3f1d7a9c524
Revises: a968d70ec211
Create Date: 2026-11-10

invoice y work_order_invoice: una factura cubre una o varias órdenes y las pasa a
Facturada. work_order_payment: el cobro, con fecha y medio, anulable. work_order_charge:
otros cargos con descripción e importe. work_order.source_order_id: la orden de la que
nació una de reparación.

Las órdenes marcadas "Facturada" en el cobro mínimo (E04-14) pasan a tener su factura y el
estado Facturada; sin número, la factura queda "S/N". work_order_billing se queda solo con
la mano de obra.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3f1d7a9c524"
down_revision: str | None = "a968d70ec211"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EVENTS = "work_order_event"
_CHECK = "ck_work_order_event_type"
_BEFORE = (
    "created",
    "status_change",
    "assigned",
    "unassigned",
    "reassigned",
    "review_approved",
    "review_returned",
    "converted_to_workshop",
    "equipment_changed",
    "materials_changed",
)
_AFTER = (*_BEFORE, "invoice_corrected", "charges_changed", "repair_order_opened")

PAYMENT_METHOD = postgresql.ENUM(
    "cash", "transfer", "check", "other", name="payment_method", create_type=False
)
BILLING_STATUS = postgresql.ENUM("pending", "invoiced", name="billing_status", create_type=False)


def _condition(event_types: tuple[str, ...]) -> str:
    return "event_type IN ({})".format(", ".join(f"'{t}'" for t in event_types))


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
    PAYMENT_METHOD.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "invoice",
        sa.Column("number", sa.String(length=50), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "work_order_invoice",
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoice.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_work_order_invoice_invoice_id"), "work_order_invoice", ["invoice_id"])
    op.create_index(
        "uq_work_order_invoice_work_order",
        "work_order_invoice",
        ["work_order_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "work_order_payment",
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("method", PAYMENT_METHOD, nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by", sa.Uuid(), nullable=True),
        sa.Column("void_reason", sa.String(length=255), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "(voided_at IS NULL) = (voided_by IS NULL AND void_reason IS NULL)",
            name="ck_work_order_payment_void",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["voided_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_work_order_payment_work_order_id"), "work_order_payment", ["work_order_id"]
    )
    op.create_index(
        "uq_work_order_payment_current",
        "work_order_payment",
        ["work_order_id"],
        unique=True,
        postgresql_where=sa.text("voided_at IS NULL AND deleted_at IS NULL"),
    )
    op.create_table(
        "work_order_charge",
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount >= 0", name="ck_work_order_charge_amount"),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_order.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_work_order_charge_work_order_id"), "work_order_charge", ["work_order_id"]
    )
    op.add_column("work_order", sa.Column("source_order_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "work_order_source_order_id_fkey", "work_order", "work_order", ["source_order_id"], ["id"]
    )
    op.create_index(op.f("ix_work_order_source_order_id"), "work_order", ["source_order_id"])

    op.drop_constraint(_CHECK, _EVENTS, type_="check")
    op.create_check_constraint(_CHECK, _EVENTS, _condition(_AFTER))

    # Las marcadas Facturada en el cobro mínimo: una factura por orden, estado Facturada y
    # su evento, con quién y cuándo la marcó.
    op.execute(
        """
        CREATE TEMP TABLE _billed ON COMMIT DROP AS
        SELECT b.work_order_id, gen_random_uuid() AS invoice_id,
               COALESCE(NULLIF(b.invoice_number, ''), 'S/N') AS number,
               b.updated_at, b.updated_by
        FROM work_order_billing b
        JOIN work_order o ON o.id = b.work_order_id
        WHERE b.status = 'invoiced' AND b.deleted_at IS NULL
          AND o.status = 'done' AND o.deleted_at IS NULL
        """
    )
    op.execute(
        """
        INSERT INTO invoice (id, number, issued_on, created_by, created_at, updated_at)
        SELECT invoice_id, number, (updated_at AT TIME ZONE 'America/Argentina/Buenos_Aires')::date,
               updated_by, updated_at, updated_at
        FROM _billed
        """
    )
    op.execute(
        """
        INSERT INTO work_order_invoice (id, work_order_id, invoice_id)
        SELECT gen_random_uuid(), work_order_id, invoice_id FROM _billed
        """
    )
    op.execute(
        """
        INSERT INTO work_order_event
            (id, work_order_id, event_type, from_status, to_status, occurred_at, actor_id, note)
        SELECT gen_random_uuid(), work_order_id, 'status_change', 'done', 'invoiced',
               updated_at, updated_by, 'Factura ' || number
        FROM _billed
        """
    )
    op.execute(
        "UPDATE work_order SET status = 'invoiced' WHERE id IN (SELECT work_order_id FROM _billed)"
    )
    op.drop_column("work_order_billing", "invoice_number")
    op.drop_column("work_order_billing", "status")
    BILLING_STATUS.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    BILLING_STATUS.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "work_order_billing",
        sa.Column("status", BILLING_STATUS, nullable=False, server_default="pending"),
    )
    op.alter_column("work_order_billing", "status", server_default=None)
    op.add_column(
        "work_order_billing", sa.Column("invoice_number", sa.String(length=50), nullable=True)
    )
    # Las facturadas y cobradas vuelven a Terminada con el cobro mínimo marcado Facturada.
    op.execute(
        """
        INSERT INTO work_order_billing
            (id, work_order_id, parts_amount, labor_amount, status, updated_by)
        SELECT gen_random_uuid(), wi.work_order_id, 0, 0, 'pending', i.created_by
        FROM work_order_invoice wi JOIN invoice i ON i.id = wi.invoice_id
        WHERE wi.deleted_at IS NULL AND NOT EXISTS (
            SELECT 1 FROM work_order_billing b
            WHERE b.work_order_id = wi.work_order_id AND b.deleted_at IS NULL
        )
        """
    )
    op.execute(
        """
        UPDATE work_order_billing b SET status = 'invoiced', invoice_number = i.number
        FROM work_order_invoice wi JOIN invoice i ON i.id = wi.invoice_id
        WHERE wi.work_order_id = b.work_order_id AND wi.deleted_at IS NULL
          AND b.deleted_at IS NULL
        """
    )
    op.execute("UPDATE work_order SET status = 'done' WHERE status IN ('invoiced', 'paid')")
    op.execute(
        "DELETE FROM work_order_event WHERE to_status IN ('invoiced', 'paid') "
        "OR from_status IN ('invoiced', 'paid') "
        "OR event_type IN ('invoice_corrected', 'charges_changed', 'repair_order_opened')"
    )
    op.drop_constraint(_CHECK, _EVENTS, type_="check")
    op.create_check_constraint(_CHECK, _EVENTS, _condition(_BEFORE))

    op.drop_index(op.f("ix_work_order_source_order_id"), table_name="work_order")
    op.drop_constraint("work_order_source_order_id_fkey", "work_order", type_="foreignkey")
    op.drop_column("work_order", "source_order_id")
    op.drop_index(op.f("ix_work_order_charge_work_order_id"), table_name="work_order_charge")
    op.drop_table("work_order_charge")
    op.drop_index("uq_work_order_payment_current", table_name="work_order_payment")
    op.drop_index(op.f("ix_work_order_payment_work_order_id"), table_name="work_order_payment")
    op.drop_table("work_order_payment")
    op.drop_index("uq_work_order_invoice_work_order", table_name="work_order_invoice")
    op.drop_index(op.f("ix_work_order_invoice_invoice_id"), table_name="work_order_invoice")
    op.drop_table("work_order_invoice")
    op.drop_table("invoice")
    PAYMENT_METHOD.drop(op.get_bind(), checkfirst=True)
