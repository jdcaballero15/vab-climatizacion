---
id: E03-04
title: "Ficha de cliente con historial"
epic: E03
phase: 1
priority: must
status: ready
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E03-01, E04-08]
blocked_by: []
assumes: []
---

# E03-04 Ficha de cliente con historial

## Historia

**Como** administración, **quiero** ver en la ficha de un cliente todas sus órdenes y lo que se hizo en cada una, **para** responder consultas y decidir con el historial a la vista.

## Criterios de aceptación

1. **Dado:** un cliente con órdenes. **Cuando:** abro su ficha. **Entonces:** veo una sección "Historial" con sus órdenes, la más nueva primero: número, fecha de creación, estado, tipo de trabajo, domicilio, equipo (si tiene) y escuadrilla (la asignada, o la que la cerró).
2. **Dado:** una orden del historial que tiene cierre (Terminada, o que volvió a Pendientes). **Cuando:** toco "Ver cierre". **Entonces:** veo lo mismo que en Terminadas: resultado, quiénes fueron, tareas, falla, reparación, estado del equipo, observación, fotos y firma o motivo.
3. **Dado:** un historial largo. **Cuando:** lo recorro. **Entonces:** está paginado (20 por página) y filtra por equipo, tipo de trabajo y período (desde y hasta, por fecha de creación).
4. **Dado:** el rol técnico. **Cuando:** pide el historial de un cliente. **Entonces:** recibe acceso denegado (403).
5. **Dado:** un cliente sin órdenes, o un filtro sin resultados. **Cuando:** abro el historial. **Entonces:** lo dice con un mensaje, sin tabla vacía.

## Fuera de alcance

- Repuestos usados: todavía no existen (E05-05). Se suman al cierre cuando se implementen.
- La línea de tiempo de cada orden (E04-06).
- La ficha del equipo con sus mediciones (E03-05).

## Notas técnicas

- Backend: `GET /admin/clients/{client_id}/orders` con `equipment_id`, `work_type_id`, `created_from`, `created_to`, `limit` y `offset`. Responde la página y el total. Para administración y dirección (`owner`); técnico 403; 404 si el cliente no existe.
- La escuadrilla sale de la asignación vigente o, si no hay, del último cierre.
- El detalle del cierre reusa `GET /admin/orders/{id}/closure` y el componente `ClosureDetail` de Órdenes (E04-08). Hoy ese endpoint es solo de administración; dirección lo suma acá, con su test.
- Web-admin: sección "Historial" en el detalle del cliente, debajo de Domicilios, Equipos y Contactos.
