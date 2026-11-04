"""Planes de mantenimiento y su generación de órdenes (E07-03 y E07-04).

Decisión de Gonza (2026-11-03): un plan por equipo, como el prototipo del cliente. Una
semana antes de cada visita se genera la orden, Pendiente, y la oficina la asigna como
cualquier otra; no hay aprobación en bloque.
"""

import calendar
import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.maintenance import (
    GeneratedOrderOut,
    MaintenancePlanAdminOut,
    MaintenancePlanCreate,
    MaintenancePlanUpdate,
    MaintenanceRunOut,
    PlanClientOut,
    PlanEquipmentOut,
    PlanNamedOut,
    PlanOpenOrderOut,
    SkippedPlanOut,
)
from app.core.dates import business_today
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.maintenance import MaintenancePlan
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.repositories.crew import CrewRepository
from app.db.repositories.equipment import EquipmentRepository
from app.db.repositories.maintenance import MaintenancePlanRepository, PlanRow
from app.db.repositories.work_order import WorkOrderRepository
from app.domain.work_order import OrderSource, OrderStatus, WorkOrderEventType
from app.services import catalog as catalog_service
from app.services import maintenance_checklist

logger = logging.getLogger(__name__)

# Con cuántos días de anticipación se genera la orden de cada visita (como el prototipo).
LEAD_DAYS = 7


class PlanNotFoundError(Exception):
    """No existe un plan con ese id."""


class PlanEquipmentNotAvailableError(Exception):
    """El equipo no existe o está dado de baja."""


class PlanWorkTypeNotAvailableError(Exception):
    """El tipo de trabajo no existe o está desactivado."""


class PlanCrewNotAvailableError(Exception):
    """La escuadrilla no existe o está desactivada."""


class EquipmentAlreadyInPlanError(Exception):
    """El equipo ya está en otro plan activo (E07-03, criterio 3)."""


def add_months(day: date, months: int) -> date:
    """El mismo día, months meses después; si ese mes no lo tiene, el último del mes."""
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def every_text(months: int) -> str:
    return "todos los meses" if months == 1 else f"cada {months} meses"


async def list_plans(
    session: AsyncSession,
    *,
    include_ended: bool,
    equipment_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
) -> list[MaintenancePlanAdminOut]:
    today = business_today()
    rows = await MaintenancePlanRepository(session).list_rows(
        today=today, include_ended=include_ended, equipment_id=equipment_id, client_id=client_id
    )
    return [_plan_out(row, today) for row in rows]


async def get_plan(session: AsyncSession, plan_id: uuid.UUID) -> MaintenancePlanAdminOut:
    plan = await _get(session, plan_id)
    return await _out(session, plan)


async def create_plan(
    session: AsyncSession, data: MaintenancePlanCreate
) -> MaintenancePlanAdminOut:
    repo = MaintenancePlanRepository(session)
    if await EquipmentRepository(session).get(data.equipment_id) is None:
        raise PlanEquipmentNotAvailableError
    await _check_work_type(session, data.work_type_id)
    if data.crew_id is not None:
        await _check_crew(session, data.crew_id)
    if await repo.equipment_has_active_plan(data.equipment_id, business_today()):
        raise EquipmentAlreadyInPlanError

    plan = MaintenancePlan(**data.model_dump())
    session.add(plan)
    try:
        await session.commit()
    except IntegrityError:
        # Otro alta del mismo equipo ganó la carrera (índice parcial).
        await session.rollback()
        raise EquipmentAlreadyInPlanError from None
    return await _out(session, plan)


async def update_plan(
    session: AsyncSession, plan_id: uuid.UUID, data: MaintenancePlanUpdate
) -> MaintenancePlanAdminOut:
    plan = await _get(session, plan_id)
    changes = data.model_dump(exclude_unset=True)
    # Sin valor no tienen sentido: null es "no lo cambio".
    for field in ("work_type_id", "every_months", "next_due_on"):
        if changes.get(field, ...) is None:
            changes.pop(field)
    if "work_type_id" in changes:
        await _check_work_type(session, changes["work_type_id"])
    if changes.get("crew_id") is not None:
        await _check_crew(session, changes["crew_id"])
    today = business_today()
    reopens = "ends_on" in changes and (changes["ends_on"] is None or changes["ends_on"] > today)
    if reopens and await MaintenancePlanRepository(session).equipment_has_active_plan(
        plan.equipment_id, today, exclude=plan.id
    ):
        raise EquipmentAlreadyInPlanError

    for field, value in changes.items():
        setattr(plan, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise EquipmentAlreadyInPlanError from None
    return await _out(session, plan)


async def _get(session: AsyncSession, plan_id: uuid.UUID) -> MaintenancePlan:
    plan = await MaintenancePlanRepository(session).get(plan_id)
    if plan is None:
        raise PlanNotFoundError
    return plan


async def _out(session: AsyncSession, plan: MaintenancePlan) -> MaintenancePlanAdminOut:
    today = business_today()
    rows = await MaintenancePlanRepository(session).list_rows(
        today=today, include_ended=True, equipment_id=plan.equipment_id
    )
    return next(_plan_out(row, today) for row in rows if row[0].id == plan.id)


async def _check_work_type(session: AsyncSession, work_type_id: uuid.UUID) -> None:
    try:
        work_type = await catalog_service.get_work_type(session, work_type_id)
    except catalog_service.WorkTypeNotFoundError:
        raise PlanWorkTypeNotAvailableError from None
    if not work_type.is_active:
        raise PlanWorkTypeNotAvailableError


async def _check_crew(session: AsyncSession, crew_id: uuid.UUID) -> None:
    crew = await CrewRepository(session).get(crew_id)
    if crew is None or not crew.is_active:
        raise PlanCrewNotAvailableError


def _plan_out(row: PlanRow, today: date) -> MaintenancePlanAdminOut:
    plan, equipment, equipment_type_name, client, site, work_type, crew, open_order = row
    return MaintenancePlanAdminOut(
        id=plan.id,
        equipment=PlanEquipmentOut(
            id=equipment.id,
            internal_code=equipment.internal_code,
            location_note=equipment.location_note,
            equipment_type_name=equipment_type_name,
        ),
        client=PlanClientOut(
            id=client.id,
            number=client.number,
            name=client.name,
            site_label=site.label,
            site_address=site.address,
        ),
        work_type=PlanNamedOut(id=work_type.id, name=work_type.name),
        crew=PlanNamedOut(id=crew.id, name=crew.name) if crew is not None else None,
        every_months=plan.every_months,
        next_due_on=plan.next_due_on,
        ends_on=plan.ends_on,
        notes=plan.notes,
        active=plan.ends_on is None or plan.ends_on > today,
        open_order=(
            PlanOpenOrderOut(
                id=open_order.id,
                number=open_order.number,
                status=open_order.status,
                due_on=open_order.maintenance_due_on,
            )
            if open_order is not None and open_order.maintenance_due_on is not None
            else None
        ),
    )


# ---- E07-04: generación de las órdenes ----


@dataclass
class _Visit:
    plan: MaintenancePlan
    equipment: Equipment
    client: Client


async def run_generation(session: AsyncSession, today: date | None = None) -> MaintenanceRunOut:
    """Genera la orden de cada visita que vence en los próximos LEAD_DAYS días.

    Corre todas las mañanas (cron) y también a pedido de la oficina. Cada visita genera una
    sola orden (índice único), así que correr dos veces no duplica. Después de generar, la
    próxima visita se corre los meses del plan; si el plan venía atrasado más de un período,
    las visitas ya pasadas no se generan.
    """
    today = today or business_today()
    repo = MaintenancePlanRepository(session)
    generated: list[GeneratedOrderOut] = []
    skipped: list[SkippedPlanOut] = []
    for plan in await repo.due_for_update(today + timedelta(days=LEAD_DAYS)):
        visit, reason = await _visit(session, plan)
        if visit is None:
            equipment = await EquipmentRepository(session).get(
                plan.equipment_id, include_deleted=True
            )
            skipped.append(
                SkippedPlanOut(
                    plan_id=plan.id,
                    equipment_code=equipment.internal_code if equipment else "",
                    reason=reason,
                )
            )
            continue
        order = await _generate(session, visit)
        if order is not None:
            generated.append(
                GeneratedOrderOut(
                    order_id=order.id,
                    number=order.number,
                    client_name=visit.client.name,
                    equipment_code=visit.equipment.internal_code,
                    due_on=plan.next_due_on,
                )
            )
        plan.next_due_on = _next_visit(plan, today)
    await session.commit()
    logger.info(
        "mantenimiento: %d órdenes generadas, %d planes omitidos", len(generated), len(skipped)
    )
    return MaintenanceRunOut(generated=generated, skipped=skipped)


async def _visit(session: AsyncSession, plan: MaintenancePlan) -> tuple[_Visit | None, str]:
    equipment = await EquipmentRepository(session).get(plan.equipment_id)
    if equipment is None:
        return None, "equipment_deleted"
    try:
        await _check_work_type(session, plan.work_type_id)
    except PlanWorkTypeNotAvailableError:
        return None, "work_type_inactive"
    site = await session.get(ClientSite, equipment.client_site_id)
    client = await session.get(Client, site.client_id) if site is not None else None
    if site is None or site.deleted_at is not None or client is None or client.deleted_at:
        return None, "equipment_deleted"
    return _Visit(plan=plan, equipment=equipment, client=client), ""


async def _generate(session: AsyncSession, visit: _Visit) -> WorkOrder | None:
    """La orden de la visita, o None si ya estaba generada."""
    plan = visit.plan
    order = WorkOrder(
        status=OrderStatus.pending,
        source=OrderSource.maintenance,
        client_id=visit.client.id,
        client_site_id=visit.equipment.client_site_id,
        equipment_id=visit.equipment.id,
        work_type_id=plan.work_type_id,
        description=plan.notes,
        maintenance_plan_id=plan.id,
        maintenance_due_on=plan.next_due_on,
    )
    try:
        async with session.begin_nested():
            session.add(order)
            await session.flush()
    except IntegrityError:
        return None
    await maintenance_checklist.copy_to_order(session, order)
    WorkOrderRepository(session).add_event(
        WorkOrderEvent(
            work_order_id=order.id,
            event_type=WorkOrderEventType.created,
            to_status=OrderStatus.pending,
            note=f"Generada por el plan de mantenimiento ({every_text(plan.every_months)}).",
        )
    )
    await session.flush()
    await session.refresh(order)
    return order


def _next_visit(plan: MaintenancePlan, today: date) -> date:
    following = add_months(plan.next_due_on, plan.every_months)
    while following < today:
        following = add_months(following, plan.every_months)
    return following
