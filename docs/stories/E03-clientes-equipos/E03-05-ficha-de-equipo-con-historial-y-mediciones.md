---
id: E03-05
title: "Ficha de equipo con historial y mediciones"
epic: E03
phase: 1
priority: must
status: draft
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E03-03, E04-06]
blocked_by: []
assumes: [D-002]
---

# E03-05 Ficha de equipo con historial y mediciones

## Historia

**Como** administración, **quiero** ver la ficha de un equipo con su historial de trabajos, repuestos y mediciones, **para** saber qué se le hizo y detectar si viene fallando.

## Criterios de aceptación

1. **Dado:** un equipo con trabajos. **Cuando:** abro su ficha. **Entonces:** veo trabajos anteriores, repuestos usados y mantenimientos y reparaciones previos.
2. **Dado:** un equipo con mediciones de mantenimiento. **Cuando:** abro su ficha. **Entonces:** veo la evolución de cada medición (ver E07-09).
3. **Dado:** un equipo migrado desde Persat. **Cuando:** abro su ficha. **Entonces:** su historial importado se distingue del generado en el sistema nuevo.
4. **Dado:** el rol técnico. **Cuando:** intenta acceder. **Entonces:** recibe acceso denegado.
