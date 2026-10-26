---
id: E05-08
title: "Elegir el resultado del trabajo"
epic: E05
phase: 1
priority: must
status: ready
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E05-04, E04-01]
blocked_by: []
assumes: []
---

# E05-08 Elegir el resultado del trabajo

## Historia

**Como** escuadrilla, **quiero** indicar al cerrar si el trabajo quedó resuelto, si hay que volver o si no se pudo hacer, **para** que la oficina sepa cómo seguir y se pueda medir qué pasa con cada orden.

## Criterios de aceptación

1. **Dado:** el formulario de cierre (E05-04). **Cuando:** elijo el resultado. **Entonces:** las opciones son "Resuelta", "Requiere otra visita" y "No se pudo hacer", agrupadas como "Se hizo" y "No se pudo", como en el prototipo.
2. **Dado:** "Resuelta". **Cuando:** envío el cierre. **Entonces:** la orden pasa a `Terminada`.
3. **Dado:** "Requiere otra visita". **Cuando:** envío el cierre. **Entonces:** la observación es obligatoria (qué falta) y la orden vuelve a `Pendiente` sin escuadrilla ni fecha, conservando lo registrado.
4. **Dado:** "No se pudo hacer". **Cuando:** lo elijo. **Entonces:** elijo el motivo de una lista fija: "Cliente ausente o sin acceso", "Falta repuesto o herramienta" o "El equipo no tiene arreglo". Al enviar, la orden vuelve a `Pendiente` sin escuadrilla ni fecha.
5. **Dado:** una orden que volvió a `Pendiente` por un cierre. **Cuando:** administración ve el listado de pendientes (E04-02). **Entonces:** ve que volvió de la escuadrilla, con el resultado, el motivo o la observación.
6. **Dado:** un cierre enviado. **Cuando:** se guarda. **Entonces:** queda un evento con el usuario de la escuadrilla, y la falla y la reparación quedan registradas por separado.

## Fuera de alcance

- "Requiere retiro" (convertir en orden de taller): llega con E06-02; hasta entonces, se usa "Requiere otra visita" con la observación.
- Cancelar desde la oficina una orden que no se pudo hacer: E04-07.
- Revisión de la orden terminada: E04-08.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26, con el prototipo del cliente:

- **"No se pudo hacer" sin estado nuevo**: el prototipo tiene el estado "No realizada"; acá es un resultado con motivo que devuelve la orden a `Pendiente` para que la oficina la reprograme o la cancele. Se mantienen los siete estados del cliente.
- **Cómo quedó el equipo** se registra aparte (E05-04), con tres opciones.

## Notas técnicas

- `closure_outcome`: `done`, `needs_revisit`, `not_done` (y `needs_pickup` cuando llegue E06-02). Motivo en `not_done_reason`.
- "Requiere otra visita" y "No se pudo hacer" usan la transición `request_revisit` (`En curso` a `Pendiente`); en la misma transacción se cierra la asignación vigente (`unassigned_at`).
- El listado de pendientes suma el último cierre de la orden (resultado y motivo u observación) para el criterio 5.
