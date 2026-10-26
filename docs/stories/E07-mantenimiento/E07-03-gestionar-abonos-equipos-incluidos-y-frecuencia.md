---
id: E07-03
title: "Gestionar abonos: equipos incluidos y frecuencia"
epic: E07
phase: 1
priority: must
status: draft
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-03, E07-01]
blocked_by: []
assumes: [D-002]
---

# E07-03 Gestionar abonos: equipos incluidos y frecuencia

## Historia

**Como** administración, **quiero** definir qué clientes son abonados, qué equipos incluye cada abono y con qué frecuencia se mantienen, **para** que el sistema genere solo el mantenimiento que corresponde.

## Criterios de aceptación

1. **Dado:** un cliente. **Cuando:** administración crea su abono y agrega equipos con frecuencia y fecha de inicio. **Entonces:** esos equipos entran en la próxima generación.
2. **Dado:** un equipo del abono. **Cuando:** administración le pone fecha de fin. **Entonces:** deja de generarse desde esa fecha y se conserva el historial.
3. **Dado:** un equipo. **Cuando:** está en más de un abono activo. **Entonces:** se rechaza.
4. **Dado:** un cambio de abono. **Cuando:** se guarda. **Entonces:** queda en la auditoría.

## Notas técnicas

- Tablas `maintenance_plan` y `maintenance_plan_equipment`. Las fechas viven en la tabla de equipos del abono (ADR 0005).

## Preguntas abiertas

- Falta el listado de clientes abonados y los equipos incluidos en cada abono (E11-06).
