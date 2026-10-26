"""Máquina de estados de la orden de trabajo (docs/architecture/order-state-machine.md).

Reglas puras: no conoce la base ni HTTP. Que el técnico sea el asignado lo controla
cada caso de uso, no esta tabla.
"""

from dataclasses import dataclass
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


class OrderKind(StrEnum):
    on_site = "on_site"
    workshop = "workshop"


class OrderSource(StrEnum):
    manual = "manual"
    maintenance = "maintenance"


class OrderChannel(StrEnum):
    whatsapp = "whatsapp"
    email = "email"
    phone = "phone"
    # En la oficina o pedido al técnico en el lugar.
    in_person = "in_person"


class WorkOrderEventType(StrEnum):
    created = "created"
    status_change = "status_change"
    assigned = "assigned"
    unassigned = "unassigned"
    reassigned = "reassigned"
    review_approved = "review_approved"
    review_returned = "review_returned"
    converted_to_workshop = "converted_to_workshop"


# Hechos que se registran en la línea de tiempo sin cambiar el estado (criterio 7).
STATUSLESS_EVENT_TYPES = frozenset(
    {
        WorkOrderEventType.reassigned,
        WorkOrderEventType.review_approved,
        WorkOrderEventType.converted_to_workshop,
    }
)


class OrderAction(StrEnum):
    assign = "assign"
    unassign = "unassign"
    start = "start"
    close_done = "close_done"
    request_revisit = "request_revisit"
    return_to_technician = "return_to_technician"
    invoice = "invoice"
    collect = "collect"
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
    Transition(_A.start, _S.assigned, _S.in_progress, _TECH, _E.status_change),
    Transition(_A.close_done, _S.in_progress, _S.done, _TECH, _E.status_change),
    Transition(_A.request_revisit, _S.in_progress, _S.pending, _TECH, _E.status_change),
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
    _A.start: "iniciar",
    _A.close_done: "cerrar",
    _A.request_revisit: "pedir otra visita",
    _A.return_to_technician: "devolver al técnico",
    _A.invoice: "facturar",
    _A.collect: "cobrar",
    _A.cancel: "cancelar",
}


class WorkOrderRuleError(Exception):
    """Pedido que la máquina de estados rechaza. Lleva el código y el mensaje para la API."""

    code: str

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


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
