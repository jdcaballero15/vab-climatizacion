"""Cierre básico de una orden desde el celular (E05-04, E05-08, E05-12)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.closure import (
    ClosureChoiceTechnicianOut,
    ClosureCreate,
    ClosureOptionsTechnicianOut,
    ClosureTechnicianOut,
    FailureChoiceTechnicianOut,
)
from app.db.models.catalog import Failure, Repair
from app.db.models.user import User
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderClosure,
    WorkOrderClosureTask,
    WorkOrderClosureTechnician,
)
from app.db.repositories.catalog import FailureRepository, RepairRepository
from app.db.repositories.crew import FieldTechnicianRepository
from app.db.repositories.work_order import WorkOrderClosureRepository, WorkOrderRepository
from app.domain.work_order import (
    NOT_DONE_REASON_LABELS,
    ClosureOutcome,
    EquipmentCondition,
    OrderAction,
    OrderStatus,
)
from app.services import catalog as catalog_service
from app.services import work_orders as work_orders_service


class ClosureValidationError(Exception):
    """Cierre incompleto o con un valor que no corresponde. Lleva el campo para la app."""

    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message


class IdempotencyKeyReusedError(Exception):
    """La clave ya se usó para el cierre de otra orden."""


# Estado en que queda la orden según el resultado (máquina de estados, E05-08).
_STATUS_AFTER = {
    ClosureOutcome.done: OrderStatus.done,
    ClosureOutcome.needs_revisit: OrderStatus.pending,
    ClosureOutcome.not_done: OrderStatus.pending,
}


async def get_closure_options(
    session: AsyncSession, user: User, order_id: uuid.UUID
) -> ClosureOptionsTechnicianOut:
    """Listas para cerrar una orden En curso de la escuadrilla del usuario."""
    order, equipment_type_id = await _order_in_progress(session, user, order_id)
    work_type = await catalog_service.get_work_type(session, order.work_type_id)
    technicians = await FieldTechnicianRepository(session).list_by_status(include_inactive=False)
    tasks = await catalog_service.list_tasks(session, order.work_type_id, include_inactive=False)
    failures: Sequence[Failure] = await _allowed(FailureRepository(session), equipment_type_id)
    repairs: Sequence[Repair] = await _allowed(RepairRepository(session), equipment_type_id)

    repairs_by_failure: dict[uuid.UUID, list[ClosureChoiceTechnicianOut]] = {}
    for repair in repairs:
        repairs_by_failure.setdefault(repair.failure_id, []).append(
            ClosureChoiceTechnicianOut(id=repair.id, name=repair.name)
        )
    return ClosureOptionsTechnicianOut(
        technicians=[ClosureChoiceTechnicianOut(id=t.id, name=t.full_name) for t in technicians],
        tasks=[ClosureChoiceTechnicianOut(id=t.id, name=t.name) for t in tasks],
        requires_failure_repair=work_type.requires_failure_repair,
        failures=[
            FailureChoiceTechnicianOut(
                id=f.id, name=f.name, repairs=repairs_by_failure.get(f.id, [])
            )
            for f in failures
        ],
    )


async def close_order(
    session: AsyncSession, user: User, order_id: uuid.UUID, data: ClosureCreate
) -> tuple[ClosureTechnicianOut, bool]:
    """Cierra la orden. Devuelve el cierre y si se creó ahora (False: reenvío, E05-12).

    Cierre, cambio de estado, fin de la asignación y evento van en una transacción.
    """
    replay = await _replay(session, user, order_id, data.idempotency_key)
    if replay is not None:
        return replay, False

    order, equipment_type_id = await _order_in_progress(session, user, order_id)
    outcome = ClosureOutcome(data.outcome)
    await _validate(session, order, equipment_type_id, outcome, data)

    action = (
        OrderAction.close_done if outcome == ClosureOutcome.done else OrderAction.request_revisit
    )
    try:
        await work_orders_service.stage_transition(
            session, order, action, user, _event_note(outcome, data)
        )
    except work_orders_service.OrderStatusConflictError:
        # Otro pedido la cerró antes: si fue este mismo cierre, es el mismo resultado.
        await session.refresh(user)
        replay = await _replay(session, user, order_id, data.idempotency_key)
        if replay is not None:
            return replay, False
        raise work_orders_service.WorkOrderNotFoundError from None
    if outcome != ClosureOutcome.done:
        await WorkOrderRepository(session).end_current_assignment(order.id)

    closure = WorkOrderClosure(
        work_order_id=order.id,
        closed_by=user.id,
        outcome=outcome,
        failure_id=data.failure_id,
        failure_other_text=data.failure_other_text,
        repair_id=data.repair_id,
        repair_other_text=data.repair_other_text,
        equipment_condition=data.equipment_condition,
        not_done_reason=data.not_done_reason,
        observation=data.observation,
        idempotency_key=data.idempotency_key,
    )
    session.add(closure)
    await session.flush()
    session.add_all(
        [
            WorkOrderClosureTechnician(closure_id=closure.id, field_technician_id=tech_id)
            for tech_id in dict.fromkeys(data.technician_ids)
        ]
        + [
            WorkOrderClosureTask(closure_id=closure.id, task_id=task_id)
            for task_id in dict.fromkeys(data.task_ids)
        ]
    )
    try:
        await session.commit()
    except IntegrityError:
        # La misma clave llegó dos veces a la vez: gana la primera.
        await session.rollback()
        await session.refresh(user)
        replay = await _replay(session, user, order_id, data.idempotency_key)
        if replay is None:
            raise
        return replay, False
    await session.refresh(closure)
    return _out(closure), True


async def _replay(
    session: AsyncSession, user: User, order_id: uuid.UUID, key: uuid.UUID
) -> ClosureTechnicianOut | None:
    existing = await WorkOrderClosureRepository(session).get_by_idempotency_key(key)
    if existing is None:
        return None
    if existing.work_order_id != order_id or existing.closed_by != user.id:
        raise IdempotencyKeyReusedError
    return _out(existing)


def _out(closure: WorkOrderClosure) -> ClosureTechnicianOut:
    return ClosureTechnicianOut(
        id=closure.id,
        outcome=closure.outcome,
        order_status=_STATUS_AFTER[closure.outcome],
        closed_at=closure.closed_at,
    )


async def _order_in_progress(
    session: AsyncSession, user: User, order_id: uuid.UUID
) -> tuple[WorkOrder, uuid.UUID | None]:
    """La orden En curso de la escuadrilla y el tipo de su equipo. Si no, no existe (404)."""
    crew = await work_orders_service.active_crew_of(session, user)
    rows = (
        await WorkOrderRepository(session).list_open_for_crew(crew.id, order_id=order_id)
        if crew is not None
        else []
    )
    if not rows or rows[0][0].status != OrderStatus.in_progress:
        raise work_orders_service.WorkOrderNotFoundError
    order, *_, equipment, _equipment_type_name = rows[0]
    return order, equipment.equipment_type_id if equipment is not None else None


async def _allowed[T: (Failure, Repair)](
    repository: FailureRepository | RepairRepository, equipment_type_id: uuid.UUID | None
) -> Sequence[T]:
    """Activas genéricas y, si la orden tiene equipo, las de su tipo (E05-04, criterio 5)."""
    model = repository.model
    extra: list[ColumnElement[bool]] = []
    if equipment_type_id is None:
        extra.append(model.equipment_type_id.is_(None))
    return await repository.list_filtered(  # type: ignore[return-value]
        equipment_type_id=equipment_type_id,
        include_specific=True,
        include_inactive=False,
        extra_filters=extra,
    )


async def _validate(
    session: AsyncSession,
    order: WorkOrder,
    equipment_type_id: uuid.UUID | None,
    outcome: ClosureOutcome,
    data: ClosureCreate,
) -> None:
    """Valida el cierre en un orden fijo: primero lo cargado, después lo que falta."""
    if not data.technician_ids:
        raise ClosureValidationError(
            "technicians_required", "technician_ids", "Tildá quiénes fueron."
        )
    active = await FieldTechnicianRepository(session).list_by_status(include_inactive=False)
    if not set(data.technician_ids) <= {t.id for t in active}:
        raise ClosureValidationError(
            "technician_not_available", "technician_ids", "Uno de los técnicos no está activo."
        )

    tasks = await catalog_service.list_tasks(session, order.work_type_id, include_inactive=False)
    if not set(data.task_ids) <= {t.id for t in tasks}:
        raise ClosureValidationError(
            "task_not_available", "task_ids", "Una de las tareas no es de este tipo de trabajo."
        )

    has_failure = data.failure_id is not None or data.failure_other_text is not None
    if data.failure_id is not None and data.failure_other_text is not None:
        raise ClosureValidationError(
            "failure_ambiguous", "failure_id", 'Elegí una falla de la lista u "Otro", no las dos.'
        )
    failures: Sequence[Failure] = await _allowed(FailureRepository(session), equipment_type_id)
    if data.failure_id is not None and data.failure_id not in {f.id for f in failures}:
        raise ClosureValidationError(
            "failure_not_available", "failure_id", "La falla no corresponde a este equipo."
        )

    if data.repair_id is not None and data.repair_other_text is not None:
        raise ClosureValidationError(
            "repair_ambiguous",
            "repair_id",
            'Elegí una reparación de la lista u "Otro", no las dos.',
        )
    has_repair = data.repair_id is not None or data.repair_other_text is not None
    if has_repair and not has_failure:
        raise ClosureValidationError(
            "repair_without_failure", "repair_id", "Elegí primero la falla."
        )
    if data.repair_id is not None:
        repairs: Sequence[Repair] = await _allowed(RepairRepository(session), equipment_type_id)
        allowed = {r.id for r in repairs if r.failure_id == data.failure_id}
        if data.repair_id not in allowed:
            raise ClosureValidationError(
                "repair_not_available", "repair_id", "La reparación no corresponde a esa falla."
            )

    work_type = await catalog_service.get_work_type(session, order.work_type_id)
    if outcome == ClosureOutcome.done and work_type.requires_failure_repair:
        if not has_failure:
            raise ClosureValidationError("failure_required", "failure_id", "Elegí la falla.")
        if not has_repair:
            raise ClosureValidationError("repair_required", "repair_id", "Elegí la reparación.")

    if outcome != ClosureOutcome.not_done and data.equipment_condition is None:
        raise ClosureValidationError(
            "equipment_condition_required",
            "equipment_condition",
            "Elegí cómo quedó el equipo.",
        )

    if outcome == ClosureOutcome.not_done and data.not_done_reason is None:
        raise ClosureValidationError(
            "not_done_reason_required", "not_done_reason", "Elegí por qué no se pudo hacer."
        )
    if outcome != ClosureOutcome.not_done and data.not_done_reason is not None:
        raise ClosureValidationError(
            "not_done_reason_not_allowed",
            "not_done_reason",
            "El motivo va solo si no se pudo hacer.",
        )

    needs_observation = (
        data.failure_other_text is not None
        or data.repair_other_text is not None
        or data.equipment_condition == EquipmentCondition.working_with_notes
        or outcome == ClosureOutcome.needs_revisit
    )
    if needs_observation and data.observation is None:
        raise ClosureValidationError(
            "observation_required", "observation", "Escribí una observación."
        )


def _event_note(outcome: ClosureOutcome, data: ClosureCreate) -> str:
    if outcome == ClosureOutcome.done:
        return "Resuelta."
    if outcome == ClosureOutcome.needs_revisit:
        return f"Requiere otra visita: {data.observation}"
    # _validate ya exige el motivo con "No se pudo hacer".
    reason = data.not_done_reason
    label = NOT_DONE_REASON_LABELS[reason] if reason is not None else "sin motivo"
    return f"No se pudo hacer: {label}."
