---
id: E04-01
title: "Máquina de estados y línea de tiempo de la orden"
epic: E04
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend]
depends_on: [E00-01, E03-02, E02-01]
blocked_by: []
assumes: []
---

# E04-01 Máquina de estados y línea de tiempo de la orden

## Historia

**Como** administración, **quiero** que las órdenes solo puedan pasar por transiciones de estado válidas y que cada cambio quede registrado, **para** no perder ninguna orden en el traspaso entre oficina y campo y poder reconstruir qué pasó.

## Criterios de aceptación

1. **Dado:** una orden en cualquier estado. **Cuando:** se intenta una transición que no está en la tabla de `order-state-machine.md`. **Entonces:** se rechaza con un error claro (código `invalid_transition`, con el estado actual y el pedido) y no se modifica nada.
2. **Dado:** una transición permitida pedida por un rol que no le corresponde (por ejemplo, administración inicia una orden o un técnico la asigna). **Cuando:** se aplica. **Entonces:** se rechaza y no se modifica nada.
3. **Dado:** una transición válida. **Cuando:** se aplica. **Entonces:** se inserta un evento con tipo, estado anterior, estado nuevo, usuario, fecha y nota, en la misma transacción que actualiza `work_order.status`.
4. **Dado:** una cancelación o una devolución al técnico. **Cuando:** se pide sin motivo. **Entonces:** se rechaza. El motivo queda en la nota del evento.
5. **Dado:** dos usuarios. **Cuando:** intentan cambiar el estado de la misma orden a la vez. **Entonces:** solo uno lo logra y el otro recibe un error de conflicto, sin evento duplicado.
6. **Dado:** una orden en `Cobrada` o `Cancelada`. **Cuando:** se intenta cambiar su estado. **Entonces:** se rechaza.
7. **Dado:** un hecho que no cambia el estado (por ejemplo, una reasignación o la aprobación de la revisión). **Cuando:** se registra. **Entonces:** queda como evento con su tipo y sin estado nuevo.
8. **Dado:** la tabla de transiciones. **Cuando:** corren los tests. **Entonces:** hay un test por cada transición permitida y por cada categoría de transición prohibida.

## Fuera de alcance

- Endpoints y pantallas: cada acción llega con su historia (crear E04-02, asignar E04-03, reasignar y desasignar E04-04, cancelar E04-07, revisar y devolver E04-08, facturar E04-09, cobrar E04-10, iniciar E05-03, cerrar E05-04 y E05-08).
- Ver la línea de tiempo en pantalla: E04-06.
- Estados calculados de la orden de taller: E06-08.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26. Se confirma la tabla de transiciones de `order-state-machine.md`:

- **Cancelar**, siempre con motivo, solo antes de `Terminada` (desde `Pendiente`, `Asignada` o `En curso`).
- **Devolver al técnico** una orden `Terminada`: vuelve a `Asignada` con el mismo técnico y un motivo.
- **"Requiere otra visita"** vuelve a `Pendiente`, sin técnico ni fecha: administración la reprograma y la puede asignar a otro.
- **Un solo técnico responsable por orden** (o por etapa, en taller). Si van dos, uno figura como responsable. *Reemplazada por D-013: la responsable es una escuadrilla.*

## Notas técnicas

- Tabla de transiciones y reglas puras en `app/domain/` (primera historia que la usa, según `backend/README.md`), sin SQLAlchemy ni FastAPI. Cada transición: estado de origen, estado de destino, acción, rol que la hace y si exige motivo.
- Transiciones permitidas: `pending → assigned` (asignar, admin), `assigned → pending` (desasignar, admin), `assigned → in_progress` (iniciar, técnico), `in_progress → done` (cerrar resuelta, técnico), `in_progress → pending` (requiere otra visita, técnico), `done → assigned` (devolver, admin, con motivo), `done → invoiced` (facturar, admin), `invoiced → paid` (cobrar, admin) y `pending | assigned | in_progress → cancelled` (cancelar, admin, con motivo). Que el técnico sea el asignado lo controla cada historia, no la tabla.
- Tablas `work_order` y `work_order_event` según `data-model.dbml`, con los enums `order_status`, `order_kind` y `order_source`. `work_order.number` sale de una secuencia de Postgres. Las columnas del pedido (canal y solicitante) las agrega E04-02.
- Un servicio aplica la transición: actualiza `status` con `WHERE status = <estado leído>` y, si no afecta ninguna fila, devuelve conflicto (409 `order_status_conflict` cuando haya API). Evento y estado van en la misma transacción. Fechas de negocio solo en `work_order_event` (ADR 0005).
- `work_order_event.event_type`: `created`, `status_change`, `assigned`, `unassigned`, `reassigned`, `review_approved`, `review_returned`, `converted_to_workshop`.

## Notas de implementación

Solo backend, sin endpoints (cada acción llega con su historia).

- Dominio puro en `app/domain/work_order.py` (primera vez que existe `app/domain/`): enums de estado, tipo, origen, tipo de evento y acción; tabla `TRANSITIONS` con origen, destino, acción, rol, tipo de evento y si exige motivo; y `resolve_transition`. Errores con código y mensaje en español: `invalid_transition` (lleva el estado actual y la acción pedida), `transition_forbidden` y `reason_required`. Un motivo vacío o de solo espacios cuenta como falta de motivo. `UserRole` se movió a `app/domain/user.py` (el dominio no puede importar `app/db/`); el modelo lo re-exporta.
- Tipo de evento de cada transición: asignar da `assigned`, desasignar `unassigned`, devolver al técnico `review_returned` y el resto `status_change`. Los hechos sin cambio de estado (`reassigned`, `review_approved`, `converted_to_workshop`) se registran con `record_event`, sin estados. `created` lo inserta E04-02 al crear la orden.
- Servicio `app/services/work_orders.py`: `apply_transition` recibe la orden tal como se leyó, hace `UPDATE ... WHERE status = <leído> RETURNING id` e inserta el evento en la misma transacción. Si el UPDATE no devuelve fila, deshace y lanza `OrderStatusConflictError` (`order_status_conflict`, 409 cuando haya API). Que el técnico sea el asignado lo controla cada historia.
- Migración `9ded0ea86f52`: enums `order_status`, `order_kind` y `order_source`, secuencia `work_order_number_seq` (de `work_order.number`) y tablas `work_order` y `work_order_event`. `event_type` es `varchar` con `CHECK` sobre los valores válidos, para no migrar un enum de Postgres por cada tipo nuevo. `occurred_at` toma `now()` de la base.
- Quedan para otras historias: `channel` y solicitante (E04-02), `requires_approval` y `maintenance_run_id` (E07, la tabla `maintenance_run` no existe aún) y el tipo `closure_in_review` que figura en `data-model.dbml` (cuando lo pida E04-08 o E05-04).
