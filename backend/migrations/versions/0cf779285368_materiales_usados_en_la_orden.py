"""materiales usados en la orden (E05-05)

Revision ID: 0cf779285368
Revises: 63b8f5e979d4
Create Date: 2026-11-02

part_usage: cada material que la escuadrilla cargó en un cierre o que administración
agregó al revisar. Suma materials_changed a los eventos válidos; al volver atrás, el
CHECK anterior se crea NOT VALID como en e7b3c9d1f024 (los eventos se conservan).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0cf779285368"
down_revision: str | None = "63b8f5e979d4"
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
)
_AFTER = (*_BEFORE, "materials_changed")


def _condition(event_types: tuple[str, ...]) -> str:
    return "event_type IN ({})".format(", ".join(f"'{t}'" for t in event_types))


def upgrade() -> None:
    op.create_table(
        "part_usage",
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("closure_id", sa.Uuid(), nullable=True),
        sa.Column("part_id", sa.Uuid(), nullable=True),
        sa.Column("other_text", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=True),
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
        sa.CheckConstraint(
            "(part_id IS NULL) <> (other_text IS NULL)", name="ck_part_usage_part_or_other"
        ),
        sa.CheckConstraint("quantity > 0", name="ck_part_usage_quantity"),
        sa.ForeignKeyConstraint(
            ["closure_id"],
            ["work_order_closure.id"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["app_user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["part_id"],
            ["part.id"],
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_order.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_part_usage_closure_id"), "part_usage", ["closure_id"], unique=False)
    op.create_index(
        op.f("ix_part_usage_work_order_id"), "part_usage", ["work_order_id"], unique=False
    )
    op.drop_constraint(_CHECK, _EVENTS, type_="check")
    op.create_check_constraint(_CHECK, _EVENTS, _condition(_AFTER))


def downgrade() -> None:
    op.drop_constraint(_CHECK, _EVENTS, type_="check")
    op.execute(
        f"ALTER TABLE {_EVENTS} ADD CONSTRAINT {_CHECK} CHECK ({_condition(_BEFORE)}) NOT VALID"
    )
    op.drop_index(op.f("ix_part_usage_work_order_id"), table_name="part_usage")
    op.drop_index(op.f("ix_part_usage_closure_id"), table_name="part_usage")
    op.drop_table("part_usage")
