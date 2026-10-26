---
id: E06-03
title: "Asignar cada etapa a una escuadrilla"
epic: E06
phase: 1
priority: must
status: draft
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E06-01, E04-03]
blocked_by: []
assumes: []
---

# E06-03 Asignar cada etapa a una escuadrilla

## Historia

**Como** administración, **quiero** asignar cada etapa de una orden de taller a una escuadrilla, que puede ser distinta en cada una, **para** repartir retiro, taller y devolución según la disponibilidad.

## Criterios de aceptación

1. **Dado:** una orden de taller. **Cuando:** asigno escuadrillas a cada etapa. **Entonces:** cada escuadrilla ve solo la etapa que le corresponde.
2. **Dado:** una etapa sin asignar. **Cuando:** se consulta el panel. **Entonces:** se muestra como pendiente de asignar.
3. **Dado:** una etapa. **Cuando:** se reasigna. **Entonces:** queda un evento y la escuadrilla anterior deja de verla.
