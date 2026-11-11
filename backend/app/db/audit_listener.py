"""Auditoría de cambios (E12-01): cada alta, cambio, baja o restauración que hace un
usuario desde la API queda en audit_event con quién, cuándo, qué entidad y las
diferencias.

Se engancha al flush de SQLAlchemy, así no depende de que cada servicio se acuerde. Solo
registra con un usuario identificado (lo pone require_role); importaciones y procesos
programados tienen su propio registro (lotes, línea de tiempo). Los datos personales y las
contraseñas no se guardan: se enmascaran.
"""

import json
import uuid
from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.db.base import TimestampedBase
from app.db.models.audit import AuditEvent

current_actor: ContextVar[uuid.UUID | None] = ContextVar("audit_actor", default=None)

# Lo que se audita: órdenes, catálogos, precios, clientes y equipos, escuadrillas,
# mantenimiento, stock y usuarios. Las tablas de detalle de un cierre no (son parte de él).
AUDITED_TABLES = frozenset(
    {
        "work_order",
        "work_order_billing",
        "work_order_charge",
        "invoice",
        "work_order_payment",
        "work_type",
        "task",
        "equipment_type",
        "failure",
        "repair",
        "part",
        "part_price",
        "part_usage",
        "client",
        "client_site",
        "client_contact",
        "equipment",
        "crew",
        "field_technician",
        "maintenance_plan",
        "maintenance_check_step",
        "stock_location",
        "stock_movement",
        "app_user",
    }
)
# DNI o CUIT y contraseñas: nunca en la auditoría (criterio 4).
MASKED = frozenset({"tax_id"})
SKIPPED = frozenset({"password_hash", "updated_at", "created_at"})
MASK = "***"


def _value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _shown(key: str, value: Any) -> Any:
    return MASK if key in MASKED and value is not None else _value(value)


def _changes(obj: TimestampedBase) -> dict[str, list[Any]]:
    changes: dict[str, list[Any]] = {}
    for attr in inspect(obj).mapper.column_attrs:
        if attr.key in SKIPPED:
            continue
        history = inspect(obj).attrs[attr.key].history
        if history.has_changes():
            old = history.deleted[0] if history.deleted else None
            new = history.added[0] if history.added else None
            if old != new:
                changes[attr.key] = [_shown(attr.key, old), _shown(attr.key, new)]
    return changes


def _created(obj: TimestampedBase) -> dict[str, list[Any]]:
    return {
        attr.key: [None, _shown(attr.key, getattr(obj, attr.key))]
        for attr in inspect(obj).mapper.column_attrs
        if attr.key not in SKIPPED and getattr(obj, attr.key) is not None
    }


def _action(changes: dict[str, list[Any]]) -> str:
    if "deleted_at" in changes:
        old, new = changes["deleted_at"]
        if old is None and new is not None:
            return "merged" if changes.get("merged_into_id", [None, None])[1] else "deactivated"
        if old is not None and new is None:
            return "restored"
    return "updated"


def _event(obj: TimestampedBase, action: str, changes: dict[str, list[Any]]) -> AuditEvent:
    return AuditEvent(
        entity=obj.__tablename__,
        entity_id=obj.id,
        action=action,
        actor_id=current_actor.get(),
        detail=json.dumps(changes, ensure_ascii=False, sort_keys=True) if changes else None,
    )


@event.listens_for(Session, "before_flush")
def _record(session: Session, flush_context: object, instances: object) -> None:
    if current_actor.get() is None:
        return
    events: list[AuditEvent] = []
    for obj in session.new:
        if isinstance(obj, TimestampedBase) and obj.__tablename__ in AUDITED_TABLES:
            if obj.id is None:
                obj.id = uuid.uuid4()
            events.append(_event(obj, "created", _created(obj)))
    for obj in session.dirty:
        if isinstance(obj, TimestampedBase) and obj.__tablename__ in AUDITED_TABLES:
            changes = _changes(obj)
            if changes:
                events.append(_event(obj, _action(changes), changes))
    session.add_all(events)
