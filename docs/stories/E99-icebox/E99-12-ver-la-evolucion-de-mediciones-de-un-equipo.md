---
id: E99-12
title: "Ver la evolución de mediciones de un equipo"
epic: E99
phase: 1
priority: could
status: icebox
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: []
blocked_by: []
assumes: [D-002]
---

# E99-12 Ver la evolución de mediciones de un equipo

> Pasó al icebox el 2026-11-10: Gonza descartó las mediciones y la aprobación en bloque del mantenimiento (decisión del 2026-11-03). Antes era E07.

## Historia

**Como** administración, **quiero** ver mes a mes cada medición de un equipo en una tabla o gráfico, **para** detectar a tiempo un equipo que viene fallando.

## Criterios de aceptación

1. **Dado:** un equipo con mediciones de varios meses. **Cuando:** abro la evolución. **Entonces:** veo cada medición en el tiempo con su rango esperado.
2. **Dado:** un valor fuera de rango. **Cuando:** lo veo en el gráfico. **Entonces:** se distingue de los demás.
3. **Dado:** el rol técnico. **Cuando:** intenta acceder. **Entonces:** recibe acceso denegado.
