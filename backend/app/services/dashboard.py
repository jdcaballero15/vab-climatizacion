"""Tablero de seguimiento (E10): indicadores calculados con los mismos filtros.

Los filtros son los del panel de órdenes (E04-05): cliente, escuadrilla, tipo de trabajo
y período por fecha de creación; el tablero suma el tipo de equipo. Las cantidades por
estado salen de la misma consulta que el panel, así coinciden (E10-01, criterio 3). Sin
precios: dirección ve importes en el panel de órdenes, no acá.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, aliased

from app.api.schemas.dashboard import (
    CountOut,
    DashboardOut,
    MaintenanceProgressOut,
    PeriodTotalsOut,
    UnbilledOrderOut,
    WeekOut,
)
from app.core.dates import BUSINESS_TZ, business_today
from app.db.models.catalog import Failure, Repair
from app.db.models.client import Client
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.equipment import Equipment
from app.db.models.part import Part, PartUsage
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderClosure,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)
from app.db.repositories.work_order import WorkOrderRepository
from app.domain.work_order import (
    ClosureOutcome,
    OrderFilters,
    OrderSource,
    OrderStatus,
    WorkOrderEventType,
)

_TOP = 10


@dataclass(frozen=True)
class DashboardFilters:
    date_from: date
    date_to: date
    client_id: uuid.UUID | None = None
    crew_id: uuid.UUID | None = None
    work_type_id: uuid.UUID | None = None
    equipment_type_id: uuid.UUID | None = None

    def orders(self) -> OrderFilters:
        """Los del panel, para que las cantidades por estado coincidan."""
        return OrderFilters(
            crew_id=self.crew_id,
            client_id=self.client_id,
            work_type_id=self.work_type_id,
            created_from=self.date_from,
            created_to=self.date_to,
        )


def default_period() -> tuple[date, date]:
    """Los últimos 30 días, hoy incluido."""
    today = business_today()
    return today - timedelta(days=29), today


def _start(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=BUSINESS_TZ)


def _scope(filters: DashboardFilters) -> list[ColumnElement[bool]]:
    """Cliente, tipo de trabajo, tipo de equipo y escuadrilla (la de la última asignación)."""
    # El historial de Persat no entra en las estadísticas (E11-03, criterio 3).
    out: list[ColumnElement[bool]] = [
        WorkOrder.deleted_at.is_(None),
        WorkOrder.source != OrderSource.persat,
    ]
    if filters.client_id is not None:
        out.append(WorkOrder.client_id == filters.client_id)
    if filters.work_type_id is not None:
        out.append(WorkOrder.work_type_id == filters.work_type_id)
    if filters.equipment_type_id is not None:
        out.append(
            WorkOrder.equipment_id.in_(
                select(Equipment.id).where(Equipment.equipment_type_id == filters.equipment_type_id)
            )
        )
    if filters.crew_id is not None:
        assignment = aliased(WorkOrderAssignment)
        last_crew = (
            select(assignment.crew_id)
            .where(assignment.work_order_id == WorkOrder.id)
            .order_by(assignment.assigned_at.desc())
            .limit(1)
            .correlate(WorkOrder)
            .scalar_subquery()
        )
        out.append(last_crew == filters.crew_id)
    return out


async def build(
    session: AsyncSession, filters: DashboardFilters, compare: tuple[date, date] | None
) -> DashboardOut:
    return DashboardOut(
        date_from=filters.date_from,
        date_to=filters.date_to,
        by_status=await _by_status(session, filters),
        weeks=await _weeks(session, filters),
        totals=await _totals(session, filters, filters.date_from, filters.date_to),
        compare=(await _totals(session, filters, compare[0], compare[1]) if compare else None),
        by_technician=await _by_technician(session, filters),
        in_progress_by_crew=await _in_progress_by_crew(session, filters),
        top_failures=await _ranking(session, filters, Failure, WorkOrderClosure.failure_id),
        top_repairs=await _ranking(session, filters, Repair, WorkOrderClosure.repair_id),
        other_failures=await _others(session, filters, WorkOrderClosure.failure_other_text),
        other_repairs=await _others(session, filters, WorkOrderClosure.repair_other_text),
        maintenance=await _maintenance(session, filters),
        unbilled=await _unbilled(session, filters),
        top_parts=await _top_parts(session, filters),
    )


async def _by_status(session: AsyncSession, filters: DashboardFilters) -> list[CountOut]:
    """Por estado, con la consulta del panel (E10-01, criterio 3)."""
    repository = WorkOrderRepository(session)
    out = []
    for status in OrderStatus:
        _, total = await repository.list_by_status_page(
            status, filters=filters.orders(), limit=1, offset=0
        )
        if filters.equipment_type_id is not None:
            total = await _count_status_with_type(session, filters, status)
        out.append(CountOut(key=status.value, label=status.value, count=total))
    return out


async def _count_status_with_type(
    session: AsyncSession, filters: DashboardFilters, status: OrderStatus
) -> int:
    created = _created_column()
    stmt = select(func.count()).where(
        WorkOrder.status == status,
        created >= _start(filters.date_from),
        created < _start(filters.date_to + timedelta(days=1)),
        *_scope(filters),
    )
    return int(await session.scalar(stmt) or 0)


def _created_column() -> ColumnElement[datetime]:
    event = aliased(WorkOrderEvent)
    return (
        select(event.occurred_at)
        .where(
            event.work_order_id == WorkOrder.id,
            event.event_type == WorkOrderEventType.created,
        )
        .limit(1)
        .correlate(WorkOrder)
        .scalar_subquery()
    )


async def _done_events(
    session: AsyncSession, filters: DashboardFilters, start: date, end: date
) -> Sequence[datetime]:
    """Cuándo pasó cada orden a Terminada en el período (una vez por orden)."""
    stmt = (
        select(func.min(WorkOrderEvent.occurred_at))
        .join(WorkOrder, WorkOrder.id == WorkOrderEvent.work_order_id)
        .where(
            WorkOrderEvent.event_type == WorkOrderEventType.status_change,
            WorkOrderEvent.to_status == OrderStatus.done,
            WorkOrderEvent.occurred_at >= _start(start),
            WorkOrderEvent.occurred_at < _start(end + timedelta(days=1)),
            *_scope(filters),
        )
        .group_by(WorkOrderEvent.work_order_id)
    )
    return (await session.scalars(stmt)).all()


async def _created_events(
    session: AsyncSession, filters: DashboardFilters, start: date, end: date
) -> Sequence[datetime]:
    stmt = (
        select(WorkOrderEvent.occurred_at)
        .join(WorkOrder, WorkOrder.id == WorkOrderEvent.work_order_id)
        .where(
            WorkOrderEvent.event_type == WorkOrderEventType.created,
            WorkOrderEvent.occurred_at >= _start(start),
            WorkOrderEvent.occurred_at < _start(end + timedelta(days=1)),
            *_scope(filters),
        )
    )
    return (await session.scalars(stmt)).all()


def _monday(moment: datetime) -> date:
    day = moment.astimezone(BUSINESS_TZ).date()
    return day - timedelta(days=day.weekday())


async def _weeks(session: AsyncSession, filters: DashboardFilters) -> list[WeekOut]:
    """Creadas y terminadas por semana (lunes a domingo), para ver la evolución."""
    created = await _created_events(session, filters, filters.date_from, filters.date_to)
    done = await _done_events(session, filters, filters.date_from, filters.date_to)
    first = filters.date_from - timedelta(days=filters.date_from.weekday())
    weeks: dict[date, WeekOut] = {}
    week = first
    while week <= filters.date_to:
        weeks[week] = WeekOut(week_start=week, created=0, done=0)
        week += timedelta(days=7)
    for moment in created:
        weeks[_monday(moment)].created += 1
    for moment in done:
        weeks[_monday(moment)].done += 1
    return list(weeks.values())


async def _totals(
    session: AsyncSession, filters: DashboardFilters, start: date, end: date
) -> PeriodTotalsOut:
    return PeriodTotalsOut(
        date_from=start,
        date_to=end,
        created=len(await _created_events(session, filters, start, end)),
        done=len(await _done_events(session, filters, start, end)),
    )


def _closures_in_period(filters: DashboardFilters) -> Select[uuid.UUID]:
    """Cierres hechos en el período, de órdenes que entran en los filtros."""
    return (
        select(WorkOrderClosure.id)
        .join(WorkOrder, WorkOrder.id == WorkOrderClosure.work_order_id)
        .where(
            WorkOrderClosure.deleted_at.is_(None),
            WorkOrderClosure.closed_at >= _start(filters.date_from),
            WorkOrderClosure.closed_at < _start(filters.date_to + timedelta(days=1)),
            *_scope(filters),
        )
    )


async def _by_technician(session: AsyncSession, filters: DashboardFilters) -> list[CountOut]:
    """Cierres en los que fue cada técnico (lo tildado al cerrar, D-013; E10-02)."""
    stmt = (
        select(FieldTechnician.id, FieldTechnician.full_name, func.count())
        .join(
            WorkOrderClosureTechnician,
            WorkOrderClosureTechnician.field_technician_id == FieldTechnician.id,
        )
        .where(WorkOrderClosureTechnician.closure_id.in_(_closures_in_period(filters)))
        .group_by(FieldTechnician.id, FieldTechnician.full_name)
        .order_by(func.count().desc(), FieldTechnician.full_name)
    )
    return [
        CountOut(key=str(tid), label=name, count=count)
        for tid, name, count in (await session.execute(stmt)).all()
    ]


async def _in_progress_by_crew(session: AsyncSession, filters: DashboardFilters) -> list[CountOut]:
    """Lo que cada escuadrilla tiene asignado o en curso ahora (no depende del período)."""
    stmt = (
        select(Crew.id, Crew.name, func.count())
        .join(WorkOrderAssignment, WorkOrderAssignment.crew_id == Crew.id)
        .join(WorkOrder, WorkOrder.id == WorkOrderAssignment.work_order_id)
        .where(
            WorkOrderAssignment.unassigned_at.is_(None),
            WorkOrderAssignment.deleted_at.is_(None),
            WorkOrder.status.in_([OrderStatus.assigned, OrderStatus.in_progress]),
            *_scope(filters),
        )
        .group_by(Crew.id, Crew.name)
        .order_by(func.count().desc(), Crew.name)
    )
    return [
        CountOut(key=str(cid), label=name, count=count)
        for cid, name, count in (await session.execute(stmt)).all()
    ]


async def _ranking(
    session: AsyncSession,
    filters: DashboardFilters,
    model: type[Failure] | type[Repair],
    column: InstrumentedAttribute[uuid.UUID | None],
) -> list[CountOut]:
    """Fallas o reparaciones más frecuentes en los cierres del período (E10-03)."""
    stmt = (
        select(model.id, model.name, func.count())
        .join(WorkOrderClosure, column == model.id)
        .where(WorkOrderClosure.id.in_(_closures_in_period(filters)))
        .group_by(model.id, model.name)
        .order_by(func.count().desc(), model.name)
        .limit(_TOP)
    )
    return [
        CountOut(key=str(item_id), label=name, count=count)
        for item_id, name, count in (await session.execute(stmt)).all()
    ]


async def _others(
    session: AsyncSession, filters: DashboardFilters, column: InstrumentedAttribute[str | None]
) -> list[CountOut]:
    """Los textos de "Otro" agrupados aparte, para sugerir sumarlos a la lista (E02-07)."""
    key = func.lower(func.trim(column))
    stmt = (
        select(key, func.min(column), func.count())
        .where(column.is_not(None), WorkOrderClosure.id.in_(_closures_in_period(filters)))
        .group_by(key)
        .order_by(func.count().desc(), key)
        .limit(_TOP)
    )
    return [
        CountOut(key=k, label=text, count=count)
        for k, text, count in (await session.execute(stmt)).all()
    ]


async def _maintenance(session: AsyncSession, filters: DashboardFilters) -> MaintenanceProgressOut:
    """Mantenimientos con visita prevista en el período: generados, asignados, cerrados,
    pendientes y cancelados (E10-04). Sin aprobación en bloque (descartada)."""
    stmt = (
        select(WorkOrder.status, func.count())
        .where(
            WorkOrder.maintenance_plan_id.is_not(None),
            WorkOrder.maintenance_due_on >= filters.date_from,
            WorkOrder.maintenance_due_on <= filters.date_to,
            *_scope(filters),
        )
        .group_by(WorkOrder.status)
    )
    counts = {status: count for status, count in (await session.execute(stmt)).all()}
    closed = sum(
        counts.get(s, 0) for s in (OrderStatus.done, OrderStatus.invoiced, OrderStatus.paid)
    )
    return MaintenanceProgressOut(
        generated=sum(counts.values()),
        pending=counts.get(OrderStatus.pending, 0),
        assigned=counts.get(OrderStatus.assigned, 0) + counts.get(OrderStatus.in_progress, 0),
        closed=closed,
        cancelled=counts.get(OrderStatus.cancelled, 0),
    )


async def _unbilled(session: AsyncSession, filters: DashboardFilters) -> list[UnbilledOrderOut]:
    """Terminadas sin facturar, la más vieja primero (E10-05). No dependen del período: si
    no se facturaron, siguen apareciendo."""
    closed_at = (
        select(func.max(WorkOrderClosure.closed_at))
        .where(
            WorkOrderClosure.work_order_id == WorkOrder.id,
            WorkOrderClosure.outcome == ClosureOutcome.done,
            WorkOrderClosure.deleted_at.is_(None),
        )
        .correlate(WorkOrder)
        .scalar_subquery()
    )
    stmt = (
        select(WorkOrder.id, WorkOrder.number, Client.name, closed_at)
        .join(Client, Client.id == WorkOrder.client_id)
        .where(WorkOrder.status == OrderStatus.done, *_scope(filters))
        .order_by(closed_at.asc().nulls_last(), WorkOrder.number)
        .limit(50)
    )
    now = datetime.now(UTC)
    return [
        UnbilledOrderOut(
            id=order_id,
            number=number,
            client_name=client_name,
            closed_at=closed,
            days=(now - closed).days if closed else None,
        )
        for order_id, number, client_name, closed in (await session.execute(stmt)).all()
    ]


async def _top_parts(session: AsyncSession, filters: DashboardFilters) -> list[CountOut]:
    """Materiales más usados en las órdenes cerradas en el período, por cantidad (E10-06)."""
    stmt = (
        select(Part.id, Part.name, Part.unit, func.sum(PartUsage.quantity))
        .join(PartUsage, PartUsage.part_id == Part.id)
        .where(
            PartUsage.deleted_at.is_(None),
            PartUsage.closure_id.in_(_closures_in_period(filters)),
        )
        .group_by(Part.id, Part.name, Part.unit)
        .order_by(func.sum(PartUsage.quantity).desc(), Part.name)
        .limit(_TOP)
    )
    return [
        CountOut(key=str(pid), label=f"{name} ({unit})", count=0, quantity=Decimal(total))
        for pid, name, unit, total in (await session.execute(stmt)).all()
    ]
