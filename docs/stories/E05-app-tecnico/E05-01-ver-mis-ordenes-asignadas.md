---
id: E05-01
title: "Ver mis órdenes asignadas"
epic: E05
phase: 1
priority: must
status: ready
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E04-03, E01-04, E00-03]
blocked_by: []
assumes: []
---

# E05-01 Ver mis órdenes asignadas

## Historia

**Como** escuadrilla, **quiero** ver en el celular la lista de las órdenes asignadas a mi escuadrilla con cliente, dirección, equipo y tarea, **para** saber a dónde ir y qué hacer.

## Criterios de aceptación

1. **Dado:** el usuario de una escuadrilla con órdenes asignadas. **Cuando:** abre la app. **Entonces:** ve el nombre de su escuadrilla y solo las órdenes `Asignada` y `En curso` de su escuadrilla, ordenadas por fecha prevista (y por número dentro del mismo día).
2. **Dado:** cada orden de la lista. **Cuando:** se muestra. **Entonces:** se ve el número, el tipo de trabajo, el estado, el comienzo de la descripción, el cliente, la dirección de la sede, el equipo (ubicación y tipo, o "Sin equipo") y la fecha prevista relativa ("Hoy", "Mañana", "Ayer" o la fecha).
3. **Dado:** una orden abierta cuya fecha prevista ya pasó (día en Argentina). **Cuando:** se muestra. **Entonces:** se marca como "Vencida".
4. **Dado:** una orden reasignada a otra escuadrilla, desasignada o cancelada. **Cuando:** la escuadrilla actualiza la lista. **Entonces:** deja de verla.
5. **Dado:** la respuesta de la API. **Cuando:** se la inspecciona. **Entonces:** no contiene precios, mano de obra, historial de clientes, quién pidió la orden ni teléfono o mail de contactos.
6. **Dado:** una escuadrilla sin órdenes abiertas. **Cuando:** abre la app. **Entonces:** ve un mensaje claro de que no tiene trabajo asignado.
7. **Dado:** un usuario técnico que no está asociado a una escuadrilla activa. **Cuando:** abre la app. **Entonces:** ve un mensaje que le pide avisar a administración, y no ve órdenes.
8. **Dado:** un usuario de administración o dirección. **Cuando:** llama a la API de la lista del técnico. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Abrir el detalle de la orden: E05-02 (la tarjeta puede quedar sin acción hasta entonces).
- La pestaña "Hechas esta semana" del prototipo: E05-14, porque depende del cierre.
- Prioridad de la orden: no existe en el sistema; si el cliente la pide, va en una historia aparte.
- Elegir la escuadrilla en el celular, como hace el prototipo: por D-013 cada celular entra con el usuario de su escuadrilla.
- Avisos al celular cuando llega una orden nueva.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26, con el prototipo del cliente:

- **Sin título propio**: el prototipo muestra un título corto, pero la orden no lo tiene. La tarjeta muestra el tipo de trabajo como etiqueta y el comienzo de la descripción (dos líneas). No se cambia la creación de órdenes (E04-02).
- **Sin prioridad**: solo se ordena por fecha prevista.
- **"Hechas esta semana"** queda para una historia aparte (E05-14).

## Notas técnicas

- Endpoint `GET /tech/orders` con `require_role(technician)`. La escuadrilla sale del usuario de la sesión (`crew.app_user_id`), nunca de un parámetro. Devuelve la escuadrilla (nombre, o nulo si el usuario no tiene una activa) y las órdenes.
- Filtra con `CREW_OPEN_STATUSES` y la asignación vigente (`unassigned_at IS NULL`) de esa escuadrilla. Sin paginar: una escuadrilla tiene pocas órdenes abiertas.
- Esquema `OrderTechnicianOut`, cubierto por el test de contrato E00-04. La sede reutiliza `ClientSiteTechnicianOut` (dirección, referencia, link de mapas, solo nombres de contacto). Del equipo, solo ubicación, tipo, marca y modelo. No incluye `requester_name` ni `channel`.
- "Hoy" y "Vencida" con el día de Argentina (`app/core/dates.py` en el backend). En la PWA, las fechas sin hora se formatean sin pasar por `Date`, como en el web-admin.
- PWA: TanStack Query; la lista se actualiza al volver a la app y con un botón "Actualizar".
