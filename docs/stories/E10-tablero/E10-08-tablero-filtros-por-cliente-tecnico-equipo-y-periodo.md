---
id: E10-08
title: "Tablero: filtros por cliente, técnico, equipo y período"
epic: E10
phase: 1
priority: should
status: done
roles: [owner, admin]
size: M
areas: [backend, web-admin]
depends_on: [E10-01]
blocked_by: []
assumes: []
---

# E10-08 Tablero: filtros por cliente, técnico, equipo y período

## Historia

**Como** dirección, **quiero** filtrar el tablero por cliente, técnico, equipo y período, y comparar entre meses, **para** analizar dónde se va el tiempo y la plata.

## Criterios de aceptación

1. **Dado:** cualquier sección del tablero. **Cuando:** aplico filtros. **Entonces:** todos los indicadores se recalculan con esos filtros.
2. **Dado:** dos períodos. **Cuando:** los comparo. **Entonces:** veo la diferencia entre ambos.
3. **Dado:** un filtro aplicado. **Cuando:** comparto la dirección web. **Entonces:** el filtro viaja en la URL.

## Notas técnicas

- Equivale a lo que daba la opción Power BI: filtros y comparación entre meses.

## Decisiones (2026-11-10)

- Sin filtro por técnico individual: la escuadrilla es la unidad de trabajo (D-013); el reparto por técnico está en E10-02.

## Hecho

- `GET /admin/dashboard` (administración y dirección; el técnico recibe 403) devuelve todas las secciones con los mismos filtros: período (por defecto los últimos 30 días), cliente, escuadrilla, tipo de trabajo y tipo de equipo. Sin precios.
- Los filtros viajan en la dirección web (`?crew_id=...&date_from=...`), así se comparten. Con "Comparar desde/hasta" se ven los totales de los dos períodos y la diferencia.
