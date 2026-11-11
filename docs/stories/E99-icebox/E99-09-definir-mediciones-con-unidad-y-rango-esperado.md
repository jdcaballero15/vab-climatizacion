---
id: E99-09
title: "Definir mediciones con unidad y rango esperado"
epic: E99
phase: 1
priority: could
status: icebox
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: []
blocked_by: []
assumes: []
---

# E99-09 Definir mediciones con unidad y rango esperado

> Pasó al icebox el 2026-11-10: Gonza descartó las mediciones y la aprobación en bloque del mantenimiento (decisión del 2026-11-03). Antes era E07.

## Historia

**Como** administración, **quiero** definir en una plantilla tareas de medición con su unidad (tensión, consumo, etc.) y un rango esperado, **para** detectar valores anormales en el momento.

## Criterios de aceptación

1. **Dado:** una plantilla. **Cuando:** agrego una tarea de tipo medición con unidad, mínimo y máximo. **Entonces:** el técnico ve la unidad ya puesta y el rango esperado.
2. **Dado:** un rango. **Cuando:** el mínimo es mayor que el máximo. **Entonces:** se rechaza.
3. **Dado:** una medición sin rango. **Cuando:** se guarda. **Entonces:** es válida y no se marca nunca fuera de rango.
