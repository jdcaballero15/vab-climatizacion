---
id: E07-06
title: "Completar el checklist de mantenimiento en la app del técnico"
epic: E07
phase: 1
priority: must
status: done
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E07-04, E05-03]
blocked_by: []
assumes: []
---

# E07-06 Completar el checklist de mantenimiento en la app del técnico

## Historia

**Como** técnico, **quiero** completar el checklist de la orden marcando cada paso como OK o No OK, **para** registrar el mantenimiento sin escribir.

## Lo acordado

Decisión de Gonza (2026-11-04): en No OK la observación es **obligatoria** (un No OK sin explicación no le sirve a la oficina). Si ningún paso pide reparación, el cierre de mantenimiento va sin falla ni reparación, aunque el tipo de trabajo las pida.

## Criterios de aceptación

1. **Dado:** una orden de mantenimiento `En curso`. **Cuando:** abro el cierre. **Entonces:** veo los pasos de su checklist con botones OK y No OK por paso.
2. **Dado:** un checklist con pasos sin responder. **Cuando:** intento terminarla. **Entonces:** se marca cuáles faltan y no se envía.
3. **Dado:** un paso en No OK. **Cuando:** lo marco. **Entonces:** tengo que escribir qué encontramos.
4. **Dado:** "Requiere otra visita" o "Requiere retiro". **Cuando:** cierro. **Entonces:** el checklist es opcional, pero si empecé a marcarlo va completo. Con "No se pudo hacer" no se muestra ni se manda.
5. **Dado:** la pantalla. **Cuando:** se inspecciona. **Entonces:** no incluye precios, mano de obra ni historial.
6. **Dado:** el checklist a medio cargar. **Cuando:** salgo y vuelvo. **Entonces:** sigue en el borrador del celular (E05-13).

## Notas técnicas

- `closure-options` trae `checklist` (id y nombre de cada paso de la orden) y, con checklist, `requires_failure_repair` en false.
- El cierre acepta `checklist: [{check_item_id, result, observation, requires_repair}]`; errores con `field: "checklist"` (`checklist_incomplete`, `checklist_observation_required`, `checklist_ok_with_details`, `checklist_item_not_available`, `checklist_not_allowed`). Tabla `work_order_closure_check`.
- Una orden de mantenimiento que pasó a taller cierra sus etapas sin checklist.
- PWA: sección "Checklist de mantenimiento" después del resultado; el borrador guarda las respuestas por id del paso.
