---
id: E05-14
title: "Ver las órdenes hechas esta semana"
epic: E05
phase: 1
priority: should
status: done
roles: [technician]
size: S
areas: [backend, pwa]
depends_on: [E05-01, E05-04]
blocked_by: []
assumes: []
---

# E05-14 Ver las órdenes hechas esta semana

## Historia

**Como** escuadrilla, **quiero** ver en el celular las órdenes que cerramos en los últimos días, **para** confirmar que el cierre llegó a la oficina sin tener que llamar.

## Criterios de aceptación

1. **Dado:** el usuario de una escuadrilla. **Cuando:** abre la pestaña "Hechas esta semana". **Entonces:** ve los cierres que su escuadrilla hizo en los últimos 7 días, del más reciente al más viejo, con un contador en la pestaña. "Para hacer" muestra también su contador.
2. **Dado:** un cierre de la lista. **Cuando:** se muestra. **Entonces:** se ven número, tipo de trabajo, cliente, dirección, el resultado ("Resuelta", "Requiere otra visita" o el motivo de "No se pudo hacer") y el día y la hora del cierre. No se puede abrir ni volver a cerrar desde el celular.
3. **Dado:** cierres con cualquier resultado. **Cuando:** se arma la lista. **Entonces:** cuentan todos, también los que devolvieron la orden a la oficina y los de órdenes que después se cancelaron o reasignaron: cuenta el cierre, no el estado actual de la orden.
4. **Dado:** un cierre de otra escuadrilla, o de hace más de 7 días. **Cuando:** se arma la lista. **Entonces:** no aparece.
5. **Dado:** la respuesta de la API. **Cuando:** se la inspecciona. **Entonces:** no contiene precios, mano de obra, historial de clientes, fotos, firmas ni quién pidió (test de contrato).
6. **Dado:** una escuadrilla sin cierres en los últimos 7 días. **Cuando:** abre la pestaña. **Entonces:** ve un mensaje claro. Un usuario sin escuadrilla activa ve el mismo aviso que en "Para hacer".

## Fuera de alcance

- Ver el detalle de un cierre ya enviado (lo cargado, fotos, firma): el técnico no ve historial.
- Retiros y devoluciones del taller (E06): se suman cuando existan.
- Filtrar o buscar en la lista.

## Notas técnicas

- Sale del prototipo del cliente (pestañas "Para hacer" y "Hechas esta semana"). Se separó de E05-01 porque depende del cierre (E05-04).
- Gonza (2026-10-28): cuentan todos los resultados, como el prototipo; "esta semana" son los últimos 7 días (no desde el lunes, así la lista no queda vacía cada lunes).
- Backend: `GET /tech/orders/done`, solo técnico (403 para el resto). Cierres con `closed_at` en los últimos 7 días (desde ahora, no por día calendario) cuya escuadrilla es la del usuario. La escuadrilla de un cierre es la de la última asignación anterior al cierre, la misma regla que `WorkOrderRepository.crew_name`. Una fila por cierre: una orden que la escuadrilla cerró con "Requiere otra visita" y después resolvió aparece dos veces. Esquema nuevo `DoneOrderTechnicianOut` (id de la orden, número, tipo, descripción, cliente, dirección, `outcome`, `not_done_reason`, `closed_at`), sin datos del cierre más allá del resultado. Ordenado por `closed_at` descendente.
- PWA: pestañas "Para hacer (n)" y "Hechas esta semana (n)" en `MyOrdersPage`; las dos listas se piden al abrir para tener los contadores. Las tarjetas de hechas no son links. Un cierre pendiente de enviar (E05-13) sigue en "Para hacer" hasta que llega.
- Implementación en dos PR: backend y PWA.
- Hecho en el backend (PR 1): `GET /tech/orders/done` (declarada antes de `/{order_id}`), `WorkOrderRepository.list_closures_for_crew` con la escuadrilla del cierre por subconsulta correlacionada, `CrewDoneOrdersTechnicianOut` con `crew` y `orders`. Sin migración.
- Hecho en la PWA (PR 2): pestañas "Para hacer (n)" y "Hechas esta semana (n)" en `MyOrdersPage`, con la pestaña en la dirección (`?vista=hechas`) para volver a la misma. `useDoneOrders` con su propia clave (`["tech", "done"]`, aparte de las de órdenes abiertas); `forgetClosedOrder` la invalida al cerrar o al mandar un pendiente. La tarjeta muestra el resultado en una etiqueta corta, el motivo de "No se pudo hacer" en su propia línea y "Hoy 17:21" / "Ayer 09:05" / la fecha con la hora de Argentina (`relativeMoment`).
