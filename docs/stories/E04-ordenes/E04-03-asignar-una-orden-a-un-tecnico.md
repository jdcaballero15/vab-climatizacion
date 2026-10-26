---
id: E04-03
title: "Asignar una orden a un técnico"
epic: E04
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-02, E01-03]
blocked_by: []
assumes: []
---

# E04-03 Asignar una orden a un técnico

## Historia

**Como** administración, **quiero** asignar una orden pendiente a un técnico con una fecha prevista, **para** que el técnico la vea en su celular y sepa cuándo ir.

## Criterios de aceptación

1. **Dado:** una orden `Pendiente`. **Cuando:** administración la asigna a un técnico activo con una fecha prevista. **Entonces:** pasa a `Asignada` con ese técnico como responsable.
2. **Dado:** una asignación. **Cuando:** se realiza. **Entonces:** queda un evento con quién asignó, a quién y para qué fecha.
3. **Dado:** el formulario de asignación. **Cuando:** se elige el técnico. **Entonces:** solo se ofrecen usuarios activos con rol técnico. Un usuario inactivo o que no es técnico se rechaza con 422.
4. **Dado:** una fecha prevista anterior a hoy o sin fecha. **Cuando:** se intenta asignar. **Entonces:** se rechaza con 422.
5. **Dado:** una orden con aprobación pendiente (`requires_approval`). **Cuando:** se intenta asignar. **Entonces:** se rechaza hasta que se apruebe el lote.
6. **Dado:** una orden que no está `Pendiente`. **Cuando:** se intenta asignar. **Entonces:** se rechaza (la reasignación es E04-04).
7. **Dado:** el listado de órdenes pendientes (E04-02). **Cuando:** administración asigna una. **Entonces:** sale del listado.
8. **Dado:** un técnico o dirección. **Cuando:** llama a la API de asignación. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Reasignar o desasignar: E04-04.
- Lo que ve el técnico en su celular: E05-01 y E05-02 (sin precios ni historial, ADR 0006).
- Avisos al técnico (push o mail).
- Franja u hora de visita.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Solo el día**: la fecha prevista no lleva hora ni franja.
- **Un solo técnico responsable** por orden. Si van dos, uno figura como responsable.
- El criterio original 5 (visibilidad para el técnico) pasa a E05-01 y E05-02, que son las que muestran la orden en el celular.

## Notas técnicas

- `work_order_assignment` según `data-model.dbml`: técnico, `scheduled_for` y `assigned_at`. La asignación vigente es la que no tiene `unassigned_at`.
- Asignación, cambio de estado (`pending → assigned`) y evento `assigned` (con técnico y fecha en la nota o en columnas del evento) en la misma transacción, con el servicio de E04-01.
- Endpoint `POST /admin/orders/{id}/assignment` con `require_role(admin)`. Errores: `order_not_found`, `invalid_transition`, `order_requires_approval`, `technician_not_available`.
- Web-admin: acción "Asignar" en el listado de pendientes, con técnico y fecha.

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): `POST /admin/orders/{id}/assignment` con `require_role(admin)`, cuerpo `technician_id` y `scheduled_for` (fecha sin hora). Devuelve la asignación (201). Estado `pending → assigned`, evento `assigned` y asignación en una transacción: `apply_transition` se separó en una parte que no confirma, para sumar la asignación.
- El evento lleva en la nota el técnico y la fecha ("Técnico: Nombre. Fecha prevista: dd/mm/aaaa."); los datos estructurados quedan en `work_order_assignment`.
- "Hoy" es el día en Argentina (`app/core/dates.py`), no el del servidor. La fecha de hoy se acepta.
- Errores: 404 `order_not_found`; 409 `invalid_transition` si la orden no está Pendiente y `order_status_conflict` si otro la cambió antes; 422 `technician_not_available` (inexistente, inactivo o sin rol técnico), `scheduled_date_in_past`, `order_requires_approval` y fecha faltante.
- Migración `c7d2f4e81a56`: tabla `work_order_assignment` con índice único parcial (una asignación vigente por orden) y `work_order.requires_approval` (`false` por defecto), que se adelantó de E07 para cubrir el criterio 5.
- Para elegir técnico, el web-admin usa `GET /admin/users` (rol y activo ya vienen en la respuesta).
- Web-admin (PR 2): botón "Asignar" en cada orden del listado de pendientes; abre debajo un formulario con técnico (solo activos con rol técnico, por nombre) y fecha prevista (mínimo hoy en Argentina). Indica lo que falta y muestra el error del backend. Al asignar, la orden sale del listado y se muestra "Orden N° X asignada a Nombre para el dd/mm/aaaa.". Las fechas sin hora se formatean sin pasar por `Date`, para que no se corran un día por UTC. Probado en el navegador contra el backend real.

