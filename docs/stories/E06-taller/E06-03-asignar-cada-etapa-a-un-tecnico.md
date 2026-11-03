---
id: E06-03
title: "Asignar cada etapa a una escuadrilla"
epic: E06
phase: 1
priority: must
status: done
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

## Refinamiento y avance

Acordado con Gonza el 2026-11-03 (escuadrillas en todo, firma y nombre sin DNI, nace desde la visita y desde la oficina, PDF más adelante, etapas en fila: opción A del ADR 0007) y hecho el mismo día:

- Cada etapa se asigna desde Pendientes como cualquier orden (opción A): la escuadrilla ve solo la etapa que le toca ("Taller · Retiro"). Reasignar deja el evento y la anterior deja de verla, como en E04-04.
