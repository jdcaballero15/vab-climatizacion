---
id: E05-02
title: "Ver el detalle de una orden asignada"
epic: E05
phase: 1
priority: must
status: in_progress
roles: [technician]
size: S
areas: [backend, pwa]
depends_on: [E05-01]
blocked_by: []
assumes: []
---

# E05-02 Ver el detalle de una orden asignada

## Historia

**Como** escuadrilla, **quiero** abrir una orden de mi lista y ver lo necesario para hacer el trabajo, **para** llegar y trabajar sin llamar a la oficina.

## Criterios de aceptación

1. **Dado:** una orden `Asignada` o `En curso` de mi escuadrilla. **Cuando:** toco su tarjeta en la lista (E05-01). **Entonces:** veo número, tipo de trabajo, estado, fecha prevista ("Hoy", "Mañana", "Ayer" o la fecha, con "Vencida" si ya pasó) y las indicaciones de la oficina (la descripción completa).
2. **Dado:** el detalle. **Cuando:** lo consulto. **Entonces:** veo el cliente, la dirección con su referencia, el sector donde se pidió (si se cargó), los nombres de los contactos del domicilio y el equipo (ubicación, tipo, marca y modelo) o "Sin equipo".
3. **Dado:** el tipo de trabajo de la orden. **Cuando:** veo el detalle. **Entonces:** veo sus tareas activas como lista de solo lectura (se tildan al cerrar, E05-04).
4. **Dado:** la dirección. **Cuando:** la toco. **Entonces:** se abre en la app de mapas del celular.
5. **Dado:** la respuesta de la API. **Cuando:** se la inspecciona. **Entonces:** no contiene precios, mano de obra, historial del cliente ni del equipo, quién pidió la orden, ni teléfono o mail de contactos.
6. **Dado:** una orden de otra escuadrilla, una que no está `Asignada` ni `En curso`, una desasignada o un id inexistente. **Cuando:** la pido por su id. **Entonces:** recibo 404, sin distinguir el motivo.
7. **Dado:** el detalle. **Cuando:** vuelvo atrás. **Entonces:** regreso a la lista de mis órdenes.
8. **Dado:** un usuario de administración o dirección. **Cuando:** llama a la API del detalle del técnico. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Iniciar la orden: E05-03 (el botón va en este detalle).
- Cerrarla: E05-04 en adelante.
- Ver órdenes cerradas: no se abren desde el celular (E05-14 las lista sin abrirlas, como el prototipo).
- Historial del cliente o del equipo.
- Teléfono o mail del contacto, y botón para llamar.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26, con el prototipo del cliente:

- **Sin historial**: la escuadrilla no ve trabajos anteriores del equipo ni del cliente. Se mantiene la regla 1 de `CLAUDE.md` y el ADR 0006; el prototipo tampoco lo muestra.
- **Contacto solo con nombre**: el prototipo muestra el teléfono, pero se mantiene lo decidido en E03-02 (ni teléfono ni mail). Queda confirmado.
- **Tareas visibles en el detalle**, de solo lectura. En el prototipo aparecen como "Pasos" en la misma pantalla del cierre.
- **Solo órdenes abiertas** de la escuadrilla. Cualquier otra responde 404.
- **Indicaciones = descripción**: la orden no tiene un campo aparte de indicaciones (el prototipo tiene título y notas). Se muestra la descripción completa.

## Notas técnicas

- Endpoint `GET /tech/orders/{id}` con `require_role(technician)`. La escuadrilla sale del usuario de la sesión, como en E05-01; mismo filtro (`CREW_OPEN_STATUSES` y asignación vigente). Si no cumple, 404 `order_not_found`.
- Esquema `OrderDetailTechnicianOut`: lo de `OrderTechnicianOut` más `requester_area` y `tasks` (nombres de las tareas activas del tipo de trabajo, por nombre como en administración; ninguna si el tipo está desactivado). Cubierto por el test de contrato E00-04.
- `today` del backend para "Hoy" y "Vencida", como en la lista.
- PWA: ruta `/ordenes/:id` (la lista pasa a `/`). La tarjeta de la lista abre el detalle. La dirección es un enlace a `map_url`.

## Notas de implementación

Se entrega en dos PR: backend primero, PWA después.

- Backend (PR 1): `GET /tech/orders/{id}` devuelve `OrderDetailTechnicianOut`, que extiende `OrderTechnicianOut` con `requester_area`, `tasks` y `today`. Usa la misma consulta que la lista (`list_open_for_crew` con un filtro opcional por id) y la misma función que arma cada orden, para que lista y detalle no se desfasen.
- Las tareas salen de `catalog.list_tasks` (solo activas, ninguna si el tipo de trabajo está desactivado), ordenadas por nombre. No hay un orden propio de tareas; si el cliente quiere ordenarlas a mano, es otra historia.
- Cualquier orden que no sea abierta y de la escuadrilla del usuario responde 404 `order_not_found`.
