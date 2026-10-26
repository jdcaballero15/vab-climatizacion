---
id: E05-04
title: "Cerrar una orden con falla y reparación de listas"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E05-03, E02-03, E02-04]
blocked_by: []
assumes: []
---

# E05-04 Cerrar una orden con falla y reparación de listas

## Historia

**Como** técnico, **quiero** elegir la falla encontrada y la reparación realizada de listas predefinidas, **para** cerrar rápido, sin escribir, y dejar datos medibles.

## Criterios de aceptación

1. **Dado:** una orden `En curso` de un equipo. **Cuando:** abro el cierre. **Entonces:** veo las fallas del tipo de equipo y las reparaciones como botones o lista, no como texto libre.
2. **Dado:** la lista de fallas o reparaciones. **Cuando:** elijo "Otro". **Entonces:** la observación pasa a ser obligatoria.
3. **Dado:** un cierre sin falla o sin reparación elegidas. **Cuando:** intento enviarlo. **Entonces:** se marca qué falta.
4. **Dado:** los listados. **Cuando:** se cargan. **Entonces:** no incluyen precios ni datos de otros clientes.

## Notas técnicas

- Cada reparación pertenece a una falla (decidido al refinar E02-04): el técnico elige primero la falla y después ve solo las reparaciones activas de esa falla y del tipo de equipo de la orden (`GET` con `failure_id` y `equipment_type_id`). "Otro" es una opción fija del cierre, no un valor del catálogo.

## Preguntas abiertas

- ¿Qué datos de cierre aplican a instalación y relevamiento? Falla y reparación tienen sentido para reparación y service.
