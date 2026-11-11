---
id: E99-11
title: "Registrar mediciones y marcar las que están fuera de rango"
epic: E99
phase: 1
priority: could
status: icebox
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: []
blocked_by: []
assumes: []
---

# E99-11 Registrar mediciones y marcar las que están fuera de rango

> Pasó al icebox el 2026-11-10: Gonza descartó las mediciones y la aprobación en bloque del mantenimiento (decisión del 2026-11-03). Antes era E07.

## Historia

**Como** técnico, **quiero** cargar los valores medidos con la unidad ya puesta y que la app me avise si están fuera de rango, **para** detectar a tiempo un equipo que viene fallando.

## Criterios de aceptación

1. **Dado:** una tarea de medición. **Cuando:** ingreso un valor. **Entonces:** se acepta solo un número y se muestra la unidad y el rango esperado.
2. **Dado:** un valor fuera del rango. **Cuando:** lo ingreso. **Entonces:** la app lo marca y pide una observación obligatoria.
3. **Dado:** un valor dentro del rango. **Cuando:** lo ingreso. **Entonces:** no se pide nada más.
4. **Dado:** el cierre enviado. **Cuando:** el servidor lo procesa. **Entonces:** guarda el valor y si estuvo fuera de rango.
