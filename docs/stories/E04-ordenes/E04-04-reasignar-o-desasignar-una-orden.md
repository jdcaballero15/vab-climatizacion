---
id: E04-04
title: "Reasignar o desasignar una orden"
epic: E04
phase: 1
priority: must
status: ready
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-03]
blocked_by: []
assumes: []
---

# E04-04 Reasignar o desasignar una orden

## Historia

**Como** administración, **quiero** cambiar la escuadrilla de una orden o quitarle la asignación, **para** reorganizar el trabajo cuando cambia el plan del día.

## Criterios de aceptación

1. **Dado:** una orden `Asignada`. **Cuando:** administración la reasigna a otra escuadrilla, con fecha prevista. **Entonces:** la escuadrilla anterior deja de verla y la nueva la ve como `Asignada`.
2. **Dado:** una orden `En curso`. **Cuando:** administración la reasigna. **Entonces:** se pide confirmación avisando que la escuadrilla la está trabajando; la orden le llega a la nueva escuadrilla como `Asignada` (la tiene que iniciar) y lo ya registrado se conserva.
3. **Dado:** una orden `Asignada`. **Cuando:** administración la desasigna. **Entonces:** vuelve a `Pendiente` sin escuadrilla ni fecha.
4. **Dado:** una orden `Pendiente` que volvió de la escuadrilla (E05-08, criterio 5). **Cuando:** administración toca "Reprogramar". **Entonces:** se abre la asignación con la misma escuadrilla y la fecha de mañana ya elegidas, que se pueden cambiar. Al confirmar queda `Asignada` y el cierre anterior se conserva.
5. **Dado:** cada reasignación, desasignación o reprogramación. **Cuando:** se realiza. **Entonces:** queda un evento con el motivo, opcional y en texto libre.
6. **Dado:** una reasignación a la misma escuadrilla y fecha, o a una escuadrilla inactiva. **Cuando:** se intenta. **Entonces:** se rechaza con el campo que falla (422).

## Fuera de alcance

- Desasignar una orden `En curso`: se reasigna o se cancela (E04-07).
- Guardar como intento un cierre que la escuadrilla anterior envía después de la reasignación: E05-13.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-27, con el prototipo del cliente:

- **Reasignar una orden `En curso` la deja `Asignada`** para la nueva escuadrilla.
- **"Reprogramar" como atajo**, como en el prototipo, pero eligiendo la fecha (mañana por defecto) y **sin borrar lo registrado en el cierre anterior**: es el caso de "hay que volver", frecuente en Persat, y perder la primera visita sería perder historial.
- **Motivo opcional**, en texto libre.

## Notas técnicas

- Por D-013 la orden se asigna a una escuadrilla, no a un técnico.
- Transiciones nuevas en la máquina de estados: `reassign` (`Asignada` a `Asignada` y `En curso` a `Asignada`). `unassign` ya existe. Cada una cierra la asignación vigente (`unassigned_at`) y, si corresponde, abre la nueva, en una transacción.
- "Reprogramar" no es una transición nueva: es la asignación de E04-03 (`Pendiente` a `Asignada`) con valores sugeridos. La escuadrilla sugerida es la de la última asignación, la misma que muestra el listado de pendientes; `returned` suma el `crew_id` para preelegirla.
- Sin modo offline (ADR 0009) no hay datos sin sincronizar. Si la escuadrilla anterior envía un cierre después del cambio, el servidor lo rechaza con 404 (ver E05-13).
