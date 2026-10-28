"""evento de cambio de equipo de la orden (E04-12)

Revision ID: e7b3c9d1f024
Revises: d1a4f7c2e958
Create Date: 2026-10-28

Suma equipment_changed a los tipos válidos de work_order_event. Al volver atrás, el
CHECK anterior se crea NOT VALID: los eventos ya registrados se conservan (nada de
borrado físico) y los nuevos tienen que ser de los tipos de antes.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7b3c9d1f024"
down_revision: str | None = "d1a4f7c2e958"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "work_order_event"
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
)
_AFTER = (*_BEFORE, "equipment_changed")


def _condition(event_types: tuple[str, ...]) -> str:
    return "event_type IN ({})".format(", ".join(f"'{t}'" for t in event_types))


def upgrade() -> None:
    op.drop_constraint(_CHECK, _TABLE, type_="check")
    op.create_check_constraint(_CHECK, _TABLE, _condition(_AFTER))


def downgrade() -> None:
    op.drop_constraint(_CHECK, _TABLE, type_="check")
    op.execute(
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CHECK} CHECK ({_condition(_BEFORE)}) NOT VALID"
    )
