import json
import uuid
from datetime import date, datetime, time, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import SessionDep, require_role
from app.core.dates import BUSINESS_TZ
from app.db.models.audit import AuditEvent
from app.db.models.user import User, UserRole

router = APIRouter(prefix="/admin/audit", tags=["auditoría"])

# Dirección y administración la consultan; nadie la edita ni la borra (criterio 3): no hay
# rutas de escritura.
AdminOrOwner = Annotated[User, Depends(require_role(UserRole.admin, UserRole.owner))]


class AuditLogOut(BaseModel):
    id: uuid.UUID
    entity: str
    entity_id: uuid.UUID
    action: str
    actor_id: uuid.UUID | None
    actor_name: str | None
    occurred_at: datetime
    # Campo: [antes, después]. Los datos personales vienen enmascarados.
    changes: dict[str, list[Any]] | None
    # Texto para lo que no es una diferencia (una unificación, por ejemplo).
    note: str | None


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int


@router.get("", response_model=AuditLogPage)
async def list_audit(
    session: SessionDep,
    _: AdminOrOwner,
    entity: str | None = None,
    actor_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    # Días de Argentina, los dos inclusive.
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogPage:
    """Cambios auditados, el más nuevo primero, filtrables por entidad, usuario y fecha."""
    stmt = select(AuditEvent, User.full_name).outerjoin(User, User.id == AuditEvent.actor_id)
    if entity:
        stmt = stmt.where(AuditEvent.entity == entity)
    if actor_id is not None:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if entity_id is not None:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    if date_from is not None:
        stmt = stmt.where(AuditEvent.occurred_at >= _day_start(date_from))
    if date_to is not None:
        stmt = stmt.where(AuditEvent.occurred_at < _day_start(date_to + timedelta(days=1)))
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await session.execute(
        stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id).limit(limit).offset(offset)
    )
    return AuditLogPage(
        items=[_out(event, name) for event, name in rows.all()],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=BUSINESS_TZ)


def _out(event: AuditEvent, actor_name: str | None) -> AuditLogOut:
    changes: dict[str, list[Any]] | None = None
    note: str | None = None
    if event.detail:
        try:
            parsed = json.loads(event.detail)
            changes = parsed if isinstance(parsed, dict) else None
        except ValueError:
            note = event.detail
    return AuditLogOut(
        id=event.id,
        entity=event.entity,
        entity_id=event.entity_id,
        action=event.action,
        actor_id=event.actor_id,
        actor_name=actor_name,
        occurred_at=event.occurred_at,
        changes=changes,
        note=note,
    )
