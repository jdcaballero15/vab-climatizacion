---
id: E04-03
title: "Asignar una orden a una escuadrilla"
epic: E04
phase: 1
priority: must
status: ready
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-02, E02-09]
blocked_by: []
assumes: []
---

# E04-03 Asignar una orden a una escuadrilla

## Historia

**Como** administración, **quiero** asignar una orden pendiente a una escuadrilla con una fecha prevista, **para** que la escuadrilla la vea en su celular y sepa cuándo ir.

## Criterios de aceptación

1. **Dado:** una orden `Pendiente`. **Cuando:** administración la asigna a una escuadrilla activa con una fecha prevista. **Entonces:** pasa a `Asignada` con esa escuadrilla como responsable.
2. **Dado:** una asignación. **Cuando:** se realiza. **Entonces:** queda un evento con quién asignó, a qué escuadrilla y para qué fecha.
3. **Dado:** el formulario de asignación. **Cuando:** se elige la escuadrilla. **Entonces:** solo se ofrecen escuadrillas activas. Una inactiva o inexistente se rechaza con 422.
4. **Dado:** una fecha prevista anterior a hoy o sin fecha. **Cuando:** se intenta asignar. **Entonces:** se rechaza con 422.
5. **Dado:** una orden con aprobación pendiente (`requires_approval`). **Cuando:** se intenta asignar. **Entonces:** se rechaza hasta que se apruebe el lote.
6. **Dado:** una orden que no está `Pendiente`. **Cuando:** se intenta asignar. **Entonces:** se rechaza (la reasignación es E04-04).
7. **Dado:** el listado de órdenes pendientes (E04-02). **Cuando:** administración asigna una. **Entonces:** sale del listado.
8. **Dado:** un técnico (usuario de escuadrilla) o dirección. **Cuando:** llama a la API de asignación. **Entonces:** recibe acceso denegado (403).
9. **Dado:** una escuadrilla con órdenes `Asignada` o `En curso`. **Cuando:** administración intenta desactivarla (E02-09). **Entonces:** se rechaza con un mensaje que pide reasignarlas antes.

## Fuera de alcance

- Reasignar o desasignar: E04-04.
- Lo que ve la escuadrilla en su celular: E05-01 y E05-02 (sin precios ni historial, ADR 0006).
- Quiénes fueron: se tilda al cerrar (E05-04), no al asignar.
- Avisos al celular (push o mail).
- Franja u hora de visita.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Solo el día**: la fecha prevista no lleva hora ni franja.
- **Una sola escuadrilla responsable** por orden (D-013, reemplaza "un solo técnico responsable").
- El criterio original 5 (visibilidad para el técnico) pasa a E05-01 y E05-02, que son las que muestran la orden en el celular.

## Cambio por D-013 (escuadrillas)

La primera versión (#171 y #172) asignaba a un **técnico** (`technician_id`, usuarios con rol técnico). Con D-013 se rehace para asignar a una **escuadrilla**:

- Migración: `work_order_assignment.technician_id` pasa a `crew_id` (referencia a `crew`). En producción todavía no hay asignaciones; en bases de prueba, las asignaciones existentes se descartan en la migración (se documenta en el PR).
- Cuerpo del endpoint: `crew_id` en lugar de `technician_id`. Error `crew_not_available` en lugar de `technician_not_available`. La nota del evento dice "Escuadrilla: Nombre. Fecha prevista: dd/mm/aaaa.".
- Web-admin: se elige la escuadrilla (de `GET /admin/crews`) en lugar del técnico.
- Se mantiene todo lo demás de la primera versión: transacción, "hoy" en Argentina, índice de una asignación vigente por orden, `requires_approval`, errores 404 y 409.

## Notas técnicas

- `work_order_assignment` según `data-model.dbml`: escuadrilla, `scheduled_for` y `assigned_at`. La asignación vigente es la que no tiene `unassigned_at`.
- Asignación, cambio de estado (`pending → assigned`) y evento `assigned` en la misma transacción, con el servicio de E04-01.
- Endpoint `POST /admin/orders/{id}/assignment` con `require_role(admin)`. Errores: `order_not_found`, `invalid_transition`, `order_requires_approval`, `crew_not_available`, `scheduled_date_in_past`.
- Web-admin: acción "Asignar" en el listado de pendientes, con escuadrilla y fecha.

## Notas de implementación (primera versión, a técnico)

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): `POST /admin/orders/{id}/assignment` con `require_role(admin)`, cuerpo `technician_id` y `scheduled_for` (fecha sin hora). Devuelve la asignación (201). Estado `pending → assigned`, evento `assigned` y asignación en una transacción: `apply_transition` se separó en una parte que no confirma, para sumar la asignación.
- El evento lleva en la nota el técnico y la fecha ("Técnico: Nombre. Fecha prevista: dd/mm/aaaa."); los datos estructurados quedan en `work_order_assignment`.
- "Hoy" es el día en Argentina (`app/core/dates.py`), no el del servidor. La fecha de hoy se acepta.
- Errores: 404 `order_not_found`; 409 `invalid_transition` si la orden no está Pendiente y `order_status_conflict` si otro la cambió antes; 422 `technician_not_available` (inexistente, inactivo o sin rol técnico), `scheduled_date_in_past`, `order_requires_approval` y fecha faltante.
- Migración `c7d2f4e81a56`: tabla `work_order_assignment` con índice único parcial (una asignación vigente por orden) y `work_order.requires_approval` (`false` por defecto), que se adelantó de E07 para cubrir el criterio 5.
- Para elegir técnico, el web-admin usa `GET /admin/users` (rol y activo ya vienen en la respuesta).
- Web-admin (PR 2): botón "Asignar" en cada orden del listado de pendientes; abre debajo un formulario con técnico (solo activos con rol técnico, por nombre) y fecha prevista (mínimo hoy en Argentina). Indica lo que falta y muestra el error del backend. Al asignar, la orden sale del listado y se muestra "Orden N° X asignada a Nombre para el dd/mm/aaaa.". Las fechas sin hora se formatean sin pasar por `Date`, para que no se corran un día por UTC. Probado en el navegador contra el backend real.

