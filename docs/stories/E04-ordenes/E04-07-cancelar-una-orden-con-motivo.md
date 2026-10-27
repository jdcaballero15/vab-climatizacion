---
id: E04-07
title: "Cancelar una orden con motivo"
epic: E04
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-01]
blocked_by: []
assumes: []
---

# E04-07 Cancelar una orden con motivo

## Historia

**Como** administración, **quiero** cancelar una orden indicando el motivo, **para** sacar del circuito lo que ya no se hará sin borrar el registro.

Reemplaza a "Eliminar" del prototipo del cliente: nada se borra, la orden queda `Cancelada` y se puede consultar.

## Criterios de aceptación

1. **Dado:** una orden `Pendiente`, `Asignada` o `En curso`. **Cuando:** administración la cancela. **Entonces:** elige el motivo de una lista fija: "Cargada por error", "Duplicada", "El cliente la canceló" u "Otro". La orden pasa a `Cancelada` y el motivo queda en el evento.
2. **Dado:** el motivo "Otro". **Cuando:** se cancela. **Entonces:** el texto es obligatorio. Sin motivo, o con "Otro" sin texto, se rechaza (en la app y en la API, 422 con el campo).
3. **Dado:** una orden `En curso`. **Cuando:** administración la cancela. **Entonces:** se pide confirmación avisando que la escuadrilla la está trabajando.
4. **Dado:** una orden `Asignada` o `En curso`. **Cuando:** se cancela. **Entonces:** termina la asignación vigente y la orden desaparece de la lista de la escuadrilla. Si la escuadrilla tenía el detalle o el cierre abierto, al actualizar o enviar ve que la orden ya no está entre las suyas (404, como en E05-02 y E05-04).
5. **Dado:** una orden `Terminada`, `Facturada`, `Cobrada` o ya `Cancelada`. **Cuando:** se intenta cancelar. **Entonces:** se rechaza (R3 y R5) y la app no ofrece la acción.
6. **Dado:** una orden `Cancelada`. **Cuando:** administración la busca. **Entonces:** la ve con el motivo, quién la canceló y cuándo, y sin acciones.

## Fuera de alcance

- Devolver al stock los repuestos de una orden `En curso` cancelada: llega con E05-05 (hoy el cierre no lleva repuestos).
- Guardar como intento un cierre que la escuadrilla envía después de la cancelación: E05-13.
- Cancelar una orden `Terminada` antes de facturar: no se permite (R3); una corrección es una orden nueva o un ajuste con auditoría (R5).

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-27, con el prototipo del cliente y lo que se usaba en Persat:

- **Cancelar reemplaza a "Eliminar"** del prototipo, con borrado lógico.
- **Lista fija de motivos más "Otro"**: en Persat el motivo era texto libre y, agrupado, casi todo era una orden mal cargada, duplicada o que el cliente ya no quería. La lista queda **a validar con la oficina**; si cambia, es un cambio de la lista, no de la historia.
- **"No se pudo realizar" no es una cancelación**: cliente ausente, clima o equipo no listo son resultados de la visita que informa la escuadrilla (E05-08). La orden vuelve a `Pendiente` y la oficina decide si reprograma (E04-04) o cancela.
- **Se puede cancelar una orden `En curso`**, con confirmación.

## Notas técnicas

- Transición `cancel` (ya en la máquina de estados, `requires_reason`). Motivo como enum `cancel_reason` (`entered_by_mistake`, `duplicate`, `client_cancelled`, `other`) más `cancel_reason_text` para "Otro"; el evento guarda el texto legible.
- En la misma transacción: transición, fin de la asignación vigente (`unassigned_at`) y evento, igual que el cierre con "requiere otra visita" (E05-08).
- Endpoint: `POST /admin/orders/{id}/cancellation` con `{reason, reason_text}`. 201 con motivo, quién y cuándo; 404 si no existe; 409 si el estado no lo permite (`invalid_transition`) o si otro la cambió a la vez (`order_status_conflict`); 422 con `field` si falta el motivo, si "Otro" no trae texto o si el texto viene con otro motivo.
- Tabla `work_order_cancellation` (una por orden) con migración `c4e8a2f6d915`.
- `GET /admin/orders?status=` acepta `pending`, `assigned`, `in_progress` y `cancelled`. Cada fila trae `assignment` (escuadrilla y fecha, en Asignadas y En curso) y `cancellation` (en canceladas, la última primero). Terminadas en adelante llegan con E04-05.
- Web-admin: selector de estado en Órdenes (Pendientes, Asignadas, En curso, Canceladas). Botón "Cancelar" en la fila, que abre un formulario propio de la app debajo (motivo, texto si es "Otro", aviso de que la escuadrilla la está trabajando si está `En curso`). Las canceladas muestran motivo, quién y cuándo, sin acciones. La acción en el detalle de la orden llega con E04-06, que todavía no tiene pantalla.
