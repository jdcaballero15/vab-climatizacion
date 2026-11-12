"""Máquina de estados de la orden de trabajo (docs/architecture/order-state-machine.md).

Reglas puras: no conoce la base ni HTTP. Que el técnico sea el asignado lo controla
cada caso de uso, no esta tabla.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from app.domain.user import UserRole


class OrderStatus(StrEnum):
    pending = "pending"
    assigned = "assigned"
    in_progress = "in_progress"
    done = "done"
    invoiced = "invoiced"
    paid = "paid"
    cancelled = "cancelled"


# Órdenes que una escuadrilla tiene entre manos: las ve en el celular (E05-01) y
# no se puede desactivar mientras tenga alguna (E04-03, criterio 9).
CREW_OPEN_STATUSES = frozenset({OrderStatus.assigned, OrderStatus.in_progress})
# Órdenes que todavía no se cerraron ni se cancelaron.
OPEN_STATUSES = frozenset({OrderStatus.pending, *CREW_OPEN_STATUSES})


@dataclass(frozen=True)
class OrderFilters:
    """Filtros del panel de órdenes (E04-05, criterio 2)."""

    crew_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    work_type_id: uuid.UUID | None = None
    created_from: date | None = None
    created_to: date | None = None


class OrderKind(StrEnum):
    on_site = "on_site"
    workshop = "workshop"


class WorkshopStage(StrEnum):
    """Etapa de una orden de taller (ADR 0007, E06). Van en fila: retiro, galpón, devolución."""

    pickup = "pickup"
    workshop = "workshop"
    delivery = "delivery"


WORKSHOP_STAGE_LABELS = {
    WorkshopStage.pickup: "Retiro",
    WorkshopStage.workshop: "Galpón",
    WorkshopStage.delivery: "Devolución",
}

# La que sigue al terminar una etapa. La devolución es la última: la orden queda Terminada.
NEXT_WORKSHOP_STAGE = {
    WorkshopStage.pickup: WorkshopStage.workshop,
    WorkshopStage.workshop: WorkshopStage.delivery,
}
# Retiro y devolución se firman: el cliente entrega o recibe el equipo (sin DNI, 2026-11-03).
SIGNED_WORKSHOP_STAGES = frozenset({WorkshopStage.pickup, WorkshopStage.delivery})


class OrderSource(StrEnum):
    manual = "manual"
    maintenance = "maintenance"
    # Historial importado de Persat (E11-03): de solo lectura y fuera del panel.
    persat = "persat"


class OrderChannel(StrEnum):
    whatsapp = "whatsapp"
    email = "email"
    phone = "phone"
    # En la oficina o pedido al técnico en el lugar.
    in_person = "in_person"


class ClosureOutcome(StrEnum):
    """Resultado del cierre de la escuadrilla (E05-08)."""

    done = "done"
    # Convierte la orden en orden de taller (E06-02); la API todavía no lo acepta.
    needs_pickup = "needs_pickup"
    needs_revisit = "needs_revisit"
    not_done = "not_done"


class EquipmentCondition(StrEnum):
    """Cómo quedó el equipo al cerrar (E05-04)."""

    working = "working"
    working_with_notes = "working_with_notes"
    not_working = "not_working"


class CheckResult(StrEnum):
    """Resultado de un paso del checklist de mantenimiento (E07-06)."""

    ok = "ok"
    not_ok = "not_ok"


class NotDoneReason(StrEnum):
    """Por qué no se pudo hacer el trabajo (E05-08). Lista fija, como el prototipo."""

    client_absent = "client_absent"
    missing_part = "missing_part"
    beyond_repair = "beyond_repair"


NOT_DONE_REASON_LABELS = {
    NotDoneReason.client_absent: "Cliente ausente o sin acceso",
    NotDoneReason.missing_part: "Falta repuesto o herramienta",
    NotDoneReason.beyond_repair: "El equipo no tiene arreglo",
}


class NoSignatureReason(StrEnum):
    """Por qué un cierre no tiene la firma del cliente (E05-07, D-011). Lista a validar."""

    client_absent = "client_absent"
    refused = "refused"
    other = "other"


NO_SIGNATURE_REASON_LABELS = {
    NoSignatureReason.client_absent: "Cliente ausente",
    NoSignatureReason.refused: "No quiso firmar",
    NoSignatureReason.other: "Otro",
}


class SignaturePurpose(StrEnum):
    """Dónde firmó el cliente. Retiro y devolución llegan con E06-04 y E06-06."""

    closure = "closure"
    pickup = "pickup"
    delivery = "delivery"


class PaymentMethod(StrEnum):
    """Cómo pagó el cliente una orden facturada (E04-10, Gonza 2026-11-10)."""

    cash = "cash"
    transfer = "transfer"
    check = "check"
    other = "other"


PAYMENT_METHOD_LABELS = {
    PaymentMethod.cash: "Efectivo",
    PaymentMethod.transfer: "Transferencia",
    PaymentMethod.check: "Cheque",
    PaymentMethod.other: "Otro",
}


class CancelReason(StrEnum):
    """Por qué administración cancela una orden (E04-07). Lista a validar con la oficina."""

    entered_by_mistake = "entered_by_mistake"
    duplicate = "duplicate"
    client_cancelled = "client_cancelled"
    # Con texto obligatorio.
    other = "other"


CANCEL_REASON_LABELS = {
    CancelReason.entered_by_mistake: "Cargada por error",
    CancelReason.duplicate: "Duplicada",
    CancelReason.client_cancelled: "El cliente la canceló",
    CancelReason.other: "Otro",
}


class WorkOrderEventType(StrEnum):
    created = "created"
    status_change = "status_change"
    assigned = "assigned"
    unassigned = "unassigned"
    reassigned = "reassigned"
    review_approved = "review_approved"
    review_returned = "review_returned"
    converted_to_workshop = "converted_to_workshop"
    # Se agregó, cambió o sacó el equipo de la orden (E04-12).
    equipment_changed = "equipment_changed"
    # Administración agregó, corrigió, sacó o pasó a la lista un material (E05-05).
    materials_changed = "materials_changed"
    # Administración corrigió el número o la fecha de la factura (E04-09, criterio 4).
    invoice_corrected = "invoice_corrected"
    # Administración agregó, corrigió o sacó un cargo de la orden (E04-11).
    charges_changed = "charges_changed"
    # Se abrió una orden de reparación a partir de esta (E04-13).
    repair_order_opened = "repair_order_opened"


# Hechos que se registran en la línea de tiempo sin cambiar el estado (criterio 7).
STATUSLESS_EVENT_TYPES = frozenset(
    {
        WorkOrderEventType.reassigned,
        WorkOrderEventType.review_approved,
        WorkOrderEventType.converted_to_workshop,
        WorkOrderEventType.equipment_changed,
        WorkOrderEventType.materials_changed,
        WorkOrderEventType.invoice_corrected,
        WorkOrderEventType.charges_changed,
        WorkOrderEventType.repair_order_opened,
    }
)


class OrderAction(StrEnum):
    assign = "assign"
    unassign = "unassign"
    reassign = "reassign"
    start = "start"
    close_done = "close_done"
    request_revisit = "request_revisit"
    # Taller (E06): termina el retiro o el galpón y la orden vuelve a Pendiente para la
    # etapa siguiente (opción A de Gonza, 2026-11-03).
    complete_stage = "complete_stage"
    return_to_technician = "return_to_technician"
    invoice = "invoice"
    collect = "collect"
    # Cobro registrado por error: vuelve a Facturada (E04-10, criterio 4).
    void_payment = "void_payment"
    cancel = "cancel"


@dataclass(frozen=True)
class Transition:
    action: OrderAction
    from_status: OrderStatus
    to_status: OrderStatus
    role: UserRole
    event_type: WorkOrderEventType
    requires_reason: bool = False


_S = OrderStatus
_A = OrderAction
_E = WorkOrderEventType
_ADMIN = UserRole.admin
_TECH = UserRole.technician

TRANSITIONS: tuple[Transition, ...] = (
    Transition(_A.assign, _S.pending, _S.assigned, _ADMIN, _E.assigned),
    Transition(_A.unassign, _S.assigned, _S.pending, _ADMIN, _E.unassigned),
    # R9: la nueva escuadrilla la recibe Asignada, también si estaba En curso (E04-04).
    Transition(_A.reassign, _S.assigned, _S.assigned, _ADMIN, _E.reassigned),
    Transition(_A.reassign, _S.in_progress, _S.assigned, _ADMIN, _E.reassigned),
    Transition(_A.start, _S.assigned, _S.in_progress, _TECH, _E.status_change),
    Transition(_A.close_done, _S.in_progress, _S.done, _TECH, _E.status_change),
    Transition(_A.request_revisit, _S.in_progress, _S.pending, _TECH, _E.status_change),
    Transition(_A.complete_stage, _S.in_progress, _S.pending, _TECH, _E.status_change),
    Transition(
        _A.return_to_technician,
        _S.done,
        _S.assigned,
        _ADMIN,
        _E.review_returned,
        requires_reason=True,
    ),
    Transition(_A.invoice, _S.done, _S.invoiced, _ADMIN, _E.status_change),
    Transition(_A.collect, _S.invoiced, _S.paid, _ADMIN, _E.status_change),
    Transition(
        _A.void_payment, _S.paid, _S.invoiced, _ADMIN, _E.status_change, requires_reason=True
    ),
    *(
        Transition(_A.cancel, origin, _S.cancelled, _ADMIN, _E.status_change, requires_reason=True)
        for origin in (_S.pending, _S.assigned, _S.in_progress)
    ),
)

_BY_KEY = {(t.from_status, t.action): t for t in TRANSITIONS}

STATUS_LABELS = {
    _S.pending: "Pendiente",
    _S.assigned: "Asignada",
    _S.in_progress: "En curso",
    _S.done: "Terminada",
    _S.invoiced: "Facturada",
    _S.paid: "Cobrada",
    _S.cancelled: "Cancelada",
}

ACTION_LABELS = {
    _A.assign: "asignar",
    _A.unassign: "desasignar",
    _A.reassign: "reasignar",
    _A.start: "iniciar",
    _A.close_done: "cerrar",
    _A.request_revisit: "pedir otra visita",
    _A.complete_stage: "terminar la etapa de",
    _A.return_to_technician: "devolver al técnico",
    _A.invoice: "facturar",
    _A.collect: "cobrar",
    _A.void_payment: "anular el cobro de",
    _A.cancel: "cancelar",
}


class WorkOrderRuleError(Exception):
    """Pedido que la máquina de estados rechaza. Lleva el código y el mensaje para la API."""

    code: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ImportedOrderReadOnlyError(WorkOrderRuleError):
    """La orden es del historial importado de Persat: no se modifica (E11-03, criterio 4)."""

    code = "imported_order_read_only"

    def __init__(self) -> None:
        super().__init__("La orden es del historial de Persat: es de solo lectura.")


class InvalidTransitionError(WorkOrderRuleError):
    code = "invalid_transition"

    def __init__(self, current: OrderStatus, action: OrderAction) -> None:
        super().__init__(
            f"No se puede {ACTION_LABELS[action]} una orden en estado {STATUS_LABELS[current]}."
        )
        self.current = current
        self.action = action


class TransitionRoleError(WorkOrderRuleError):
    code = "transition_forbidden"

    def __init__(self, action: OrderAction, role: UserRole) -> None:
        super().__init__(f"Tu rol no puede {ACTION_LABELS[action]} una orden.")
        self.action = action
        self.role = role


class ReasonRequiredError(WorkOrderRuleError):
    code = "reason_required"

    def __init__(self, action: OrderAction) -> None:
        super().__init__("Indicá el motivo.")
        self.action = action


def resolve_transition(
    current: OrderStatus, action: OrderAction, role: UserRole, note: str | None
) -> Transition:
    """Devuelve la transición a aplicar o lanza el error que corresponde."""
    transition = _BY_KEY.get((current, action))
    if transition is None:
        raise InvalidTransitionError(current, action)
    if role != transition.role:
        raise TransitionRoleError(action, role)
    if transition.requires_reason and not (note and note.strip()):
        raise ReasonRequiredError(action)
    return transition
