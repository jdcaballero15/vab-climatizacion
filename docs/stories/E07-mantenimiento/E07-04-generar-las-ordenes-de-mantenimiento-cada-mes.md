---
id: E07-04
title: "Generar las órdenes de mantenimiento cada mes"
epic: E07
phase: 1
priority: must
status: done
roles: [admin]
size: L
areas: [backend, web-admin, infra]
depends_on: [E07-03, E04-02]
blocked_by: []
assumes: [D-005]
---

# E07-04 Generar las órdenes de mantenimiento cada mes

## Historia

**Como** administración, **quiero** que el sistema genere sola la orden de cada visita de mantenimiento, con anticipación, **para** no crear a mano decenas de órdenes (hoy son unos 60 equipos en dos días).

## Lo acordado

Decisión de Gonza (2026-11-03): **una semana antes de cada visita** se genera la orden, **Pendiente**, y la oficina la asigna o cancela como cualquier otra. **Sin aprobación en bloque** (E99-10 se descarta y `requires_approval` queda sin uso). Al asignar, viene elegida la escuadrilla del plan y el día de la visita.

## Criterios de aceptación

1. **Dado:** un plan con una visita en los próximos 7 días. **Cuando:** corre el proceso de cada mañana. **Entonces:** genera una orden `source = maintenance` Pendiente, con el equipo, el domicilio, el tipo de trabajo y las indicaciones del plan, y corre la próxima visita los meses del plan.
2. **Dado:** el proceso. **Cuando:** se ejecuta dos veces, o a la vez que "Generar ahora". **Entonces:** no duplica órdenes (una orden por plan y día de visita, índice único).
3. **Dado:** un plan atrasado más de un período. **Cuando:** se genera. **Entonces:** genera una sola orden y la próxima visita queda desde hoy en adelante.
4. **Dado:** un plan cuyo equipo o cliente está dado de baja, o cuyo tipo de trabajo se desactivó. **Cuando:** se genera. **Entonces:** se omite y queda en el resumen con el motivo.
5. **Dado:** una corrida. **Cuando:** termina. **Entonces:** queda un resumen con cuántas se generaron y cuántas se omitieron y por qué: en el log del proceso y en la pantalla con "Generar ahora".
6. **Dado:** una orden generada. **Cuando:** la oficina la ve en Pendientes. **Entonces:** se distingue como "Mantenimiento · para el dd/mm/aaaa" y, al asignar, viene con la escuadrilla del plan y el día de la visita (o hoy, si ya pasó).

## Notas técnicas

- `app/services/maintenance.py` (`run_generation`). Los planes se bloquean con `FOR UPDATE SKIP LOCKED`. Sumar meses usa el último día del mes si ese día no existe (31/1 + 1 = 28/2).
- Cron de Render `vab-ot-maintenance` (`python -m app.maintenance_run`, 6 de la mañana en Argentina), igual que el de las copias. E00-11 (jobs en general) sigue abierta.
- `POST /admin/maintenance/run` ("Generar ahora") corre lo mismo.
- `work_order.maintenance_plan_id` y `maintenance_due_on`; `OrderListItemOut.maintenance` con el día, la frecuencia y la escuadrilla del plan.
