---
id: E10-04
title: "Tablero: avance del mantenimiento preventivo"
epic: E10
phase: 1
priority: must
status: done
roles: [owner, admin]
size: S
areas: [backend, web-admin]
depends_on: [E10-01, E07-04]
blocked_by: []
assumes: []
---

# E10-04 Tablero: avance del mantenimiento preventivo

## Historia

**Como** dirección, **quiero** ver cuántas órdenes de mantenimiento del mes se generaron, se aprobaron y se cerraron, **para** saber si el preventivo va al día.

## Criterios de aceptación

1. **Dado:** una corrida mensual. **Cuando:** abro la sección. **Entonces:** veo generadas, aprobadas, asignadas, cerradas y pendientes.
2. **Dado:** un mes anterior. **Cuando:** lo elijo. **Entonces:** veo su avance final.

## Decisiones (2026-11-10)

- Sin "aprobadas": la aprobación en bloque se descartó (E99-10).

## Hecho

- `GET /admin/dashboard` (administración y dirección; el técnico recibe 403) devuelve todas las secciones con los mismos filtros: período (por defecto los últimos 30 días), cliente, escuadrilla, tipo de trabajo y tipo de equipo. Sin precios.
- Mantenimientos con visita prevista en el período: generados, pendientes, asignados (o en curso), cerrados y cancelados. Un mes anterior se ve eligiendo su período.
