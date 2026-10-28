---
id: E04-12
title: "Asociar un equipo a la orden"
epic: E04
phase: 1
priority: must
status: in_progress
roles: [admin]
size: S
areas: [backend, web-admin, pwa]
depends_on: [E04-02, E03-03]
blocked_by: []
assumes: [D-002]
---

# E04-12 Asociar un equipo a la orden

## Historia

**Como** administración, **quiero** elegir sobre qué equipo del cliente se hará el trabajo, **para** que cada trabajo quede en el historial del equipo.

## Criterios de aceptación

1. **Dado:** una orden nueva de un cliente con equipos en el domicilio elegido. **Cuando:** la creo. **Entonces:** puedo elegir un equipo, y solo se ofrecen los de ese domicilio (código, tipo, ubicación, marca y modelo). Si cambio de domicilio, el equipo elegido se borra.
2. **Dado:** cualquier tipo de trabajo. **Cuando:** creo la orden sin equipo. **Entonces:** se crea igual: el equipo es opcional siempre.
3. **Dado:** una orden `Pendiente` o `Asignada`. **Cuando:** agrego, cambio o saco el equipo. **Entonces:** se guarda y la escuadrilla lo ve en el celular la próxima vez que actualiza. En `En curso` o después ya no se puede (409).
4. **Dado:** un equipo de otro domicilio, de otro cliente o dado de baja. **Cuando:** se intenta asociar. **Entonces:** la API lo rechaza (422, campo `equipment_id`).
5. **Dado:** el listado de órdenes de la oficina. **Cuando:** una orden tiene equipo. **Entonces:** se ve cuál es (código y ubicación).
6. **Dado:** el técnico. **Cuando:** ve la orden en el celular. **Entonces:** ve el equipo como hasta ahora (ubicación, tipo, marca y modelo) y no lo puede cambiar.
7. **Dado:** un técnico o dirección. **Cuando:** intenta cambiar el equipo de una orden. **Entonces:** recibe 403.

## Fuera de alcance

- Que algunos tipos de trabajo exijan equipo (se puede sumar después marcándolo en el tipo).
- Varios equipos por orden: si hay que atender 3 equipos, son 3 órdenes.
- Elegir o corregir el equipo desde el celular al cerrar: si está mal, el técnico lo anota en la observación.
- La ficha del equipo con su historial de trabajos (E03-05). Este criterio salía acá y se pasa a esa historia: con el equipo en la orden, el historial sale de las órdenes cerradas.

## Notas técnicas

- Gonza (2026-10-28): siempre opcional, uno por orden, se puede cambiar hasta que se inicie, el técnico no lo elige.
- La columna `work_order.equipment_id` ya existe y el celular ya muestra el equipo (`EquipmentTechnicianOut`, E05-01 y E05-02): no hay migración.
- Backend: `WorkOrderCreate` suma `equipment_id` opcional. `PUT /admin/orders/{id}/equipment` con `{"equipment_id": uuid | null}`, solo administración (como crear la orden), 409 `order_not_editable` fuera de `Pendiente` y `Asignada`. Validación común al crear y al cambiar: el equipo existe, no está dado de baja y es del domicilio de la orden (422 `equipment_not_available`, campo `equipment_id`). Evento sin cambio de estado `equipment_changed` en la línea de tiempo, con el código anterior y el nuevo (suma un valor al CHECK `ck_work_order_event_type`: migración reversible). `OrderListItemOut` suma `equipment` (código y ubicación), nulo sin equipo.
- web-admin: en "Nueva orden", selector de equipo debajo del domicilio con los equipos de `GET /admin/clients/{id}/equipment?site_id=`, "Sin equipo" por defecto. En la tarjeta de la orden, el equipo, y en "Más acciones" de Pendientes y Asignadas, "Cambiar equipo" con el mismo selector.
- Implementación en dos PR: backend y web-admin.
- Hecho en el backend (PR 1): `WorkOrderCreate.equipment_id`, `PUT /admin/orders/{id}/equipment` (`EquipmentChange`), validación común `_check_equipment` (equipo vigente del domicilio de la orden), cambio condicionado al estado con `update_equipment_if` (si la escuadrilla la inicia en el medio, 409), evento `equipment_changed` con nota "Equipo: EA1 -> EA2" (o "sin equipo"); elegir el mismo no registra nada. `WorkOrderAdminOut.equipment_id` y `OrderListItemOut.equipment` (id, código y ubicación). Migración `e7b3c9d1f024` (solo el CHECK de `work_order_event`; al volver atrás queda `NOT VALID` y conserva los eventos).
