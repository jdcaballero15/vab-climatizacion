---
id: E07-09
title: "Ver la evolución de mediciones de un equipo"
epic: E07
phase: 1
priority: should
status: draft
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E07-07, E03-05]
blocked_by: []
assumes: [D-002]
---

# E07-09 Ver la evolución de mediciones de un equipo

## Historia

**Como** administración, **quiero** ver mes a mes cada medición de un equipo en una tabla o gráfico, **para** detectar a tiempo un equipo que viene fallando.

## Criterios de aceptación

1. **Dado:** un equipo con mediciones de varios meses. **Cuando:** abro la evolución. **Entonces:** veo cada medición en el tiempo con su rango esperado.
2. **Dado:** un valor fuera de rango. **Cuando:** lo veo en el gráfico. **Entonces:** se distingue de los demás.
3. **Dado:** el rol técnico. **Cuando:** intenta acceder. **Entonces:** recibe acceso denegado.
