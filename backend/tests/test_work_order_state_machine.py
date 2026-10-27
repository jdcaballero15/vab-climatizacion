import pytest

from app.domain.user import UserRole
from app.domain.work_order import (
    TRANSITIONS,
    InvalidTransitionError,
    OrderAction,
    OrderStatus,
    ReasonRequiredError,
    TransitionRoleError,
    WorkOrderEventType,
    resolve_transition,
)

# E04-01: reglas puras de la máquina de estados, sin base de datos.

ADMIN = UserRole.admin
TECH = UserRole.technician

# Criterio 8: una fila por cada transición permitida de order-state-machine.md.
PERMITIDAS = [
    (OrderStatus.pending, OrderAction.assign, ADMIN, OrderStatus.assigned),
    (OrderStatus.assigned, OrderAction.unassign, ADMIN, OrderStatus.pending),
    (OrderStatus.assigned, OrderAction.reassign, ADMIN, OrderStatus.assigned),
    (OrderStatus.in_progress, OrderAction.reassign, ADMIN, OrderStatus.assigned),
    (OrderStatus.assigned, OrderAction.start, TECH, OrderStatus.in_progress),
    (OrderStatus.in_progress, OrderAction.close_done, TECH, OrderStatus.done),
    (OrderStatus.in_progress, OrderAction.request_revisit, TECH, OrderStatus.pending),
    (OrderStatus.done, OrderAction.return_to_technician, ADMIN, OrderStatus.assigned),
    (OrderStatus.done, OrderAction.invoice, ADMIN, OrderStatus.invoiced),
    (OrderStatus.invoiced, OrderAction.collect, ADMIN, OrderStatus.paid),
    (OrderStatus.pending, OrderAction.cancel, ADMIN, OrderStatus.cancelled),
    (OrderStatus.assigned, OrderAction.cancel, ADMIN, OrderStatus.cancelled),
    (OrderStatus.in_progress, OrderAction.cancel, ADMIN, OrderStatus.cancelled),
]

CON_MOTIVO = {OrderAction.cancel, OrderAction.return_to_technician}


def test_la_tabla_tiene_exactamente_las_transiciones_permitidas() -> None:
    en_tabla = {(t.from_status, t.action, t.role, t.to_status) for t in TRANSITIONS}
    assert en_tabla == set(PERMITIDAS)


@pytest.mark.parametrize(("origen", "accion", "rol", "destino"), PERMITIDAS)
def test_transicion_permitida(
    origen: OrderStatus, accion: OrderAction, rol: UserRole, destino: OrderStatus
) -> None:
    nota = "Motivo de prueba" if accion in CON_MOTIVO else None
    transition = resolve_transition(origen, accion, rol, nota)
    assert transition.to_status == destino


# Criterio 1: una transición que no está en la tabla se rechaza con el estado y el pedido.
@pytest.mark.parametrize(
    ("origen", "accion"),
    [
        (OrderStatus.pending, OrderAction.start),
        (OrderStatus.pending, OrderAction.invoice),
        (OrderStatus.assigned, OrderAction.close_done),
        (OrderStatus.done, OrderAction.cancel),
        (OrderStatus.invoiced, OrderAction.cancel),
        (OrderStatus.done, OrderAction.collect),
    ],
)
def test_transicion_inexistente_se_rechaza(origen: OrderStatus, accion: OrderAction) -> None:
    with pytest.raises(InvalidTransitionError) as exc:
        resolve_transition(origen, accion, ADMIN, "Motivo")
    assert exc.value.code == "invalid_transition"
    assert exc.value.current == origen
    assert exc.value.action == accion


# Criterio 2: transición permitida pedida por un rol que no le corresponde.
@pytest.mark.parametrize(
    ("origen", "accion", "rol"),
    [
        (OrderStatus.assigned, OrderAction.start, ADMIN),
        (OrderStatus.pending, OrderAction.assign, TECH),
        (OrderStatus.in_progress, OrderAction.cancel, TECH),
        (OrderStatus.done, OrderAction.invoice, UserRole.owner),
    ],
)
def test_rol_equivocado_se_rechaza(origen: OrderStatus, accion: OrderAction, rol: UserRole) -> None:
    with pytest.raises(TransitionRoleError):
        resolve_transition(origen, accion, rol, "Motivo")


# Criterio 4: cancelar o devolver al técnico sin motivo se rechaza.
@pytest.mark.parametrize(
    ("origen", "accion"),
    [
        (OrderStatus.pending, OrderAction.cancel),
        (OrderStatus.done, OrderAction.return_to_technician),
    ],
)
@pytest.mark.parametrize("nota", [None, "", "   "])
def test_falta_de_motivo_se_rechaza(
    origen: OrderStatus, accion: OrderAction, nota: str | None
) -> None:
    with pytest.raises(ReasonRequiredError):
        resolve_transition(origen, accion, ADMIN, nota)


# Criterio 6: Cobrada y Cancelada son finales.
@pytest.mark.parametrize("final", [OrderStatus.paid, OrderStatus.cancelled])
@pytest.mark.parametrize("accion", list(OrderAction))
@pytest.mark.parametrize("rol", [ADMIN, TECH])
def test_estado_final_no_cambia(final: OrderStatus, accion: OrderAction, rol: UserRole) -> None:
    with pytest.raises(InvalidTransitionError):
        resolve_transition(final, accion, rol, "Motivo")


def test_tipo_de_evento_de_cada_transicion() -> None:
    by_action = {t.action: t.event_type for t in TRANSITIONS}
    assert by_action[OrderAction.assign] == WorkOrderEventType.assigned
    assert by_action[OrderAction.unassign] == WorkOrderEventType.unassigned
    assert by_action[OrderAction.reassign] == WorkOrderEventType.reassigned
    assert by_action[OrderAction.return_to_technician] == WorkOrderEventType.review_returned
    assert by_action[OrderAction.start] == WorkOrderEventType.status_change
