---
id: E10-06
title: "Tablero: repuestos más usados"
epic: E10
phase: 1
priority: must
status: done
roles: [owner, admin]
size: S
areas: [backend, web-admin]
depends_on: [E10-01, E08-04]
blocked_by: []
assumes: []
---

# E10-06 Tablero: repuestos más usados

## Historia

**Como** dirección, **quiero** ver qué repuestos se usan más, **para** planificar compras y stock.

## Criterios de aceptación

1. **Dado:** usos de repuestos en el período. **Cuando:** abro la sección. **Entonces:** veo el ranking de repuestos por cantidad usada.
2. **Dado:** el ranking. **Cuando:** filtro por período, técnico o tipo de equipo. **Entonces:** se actualiza.

## Decisiones (2026-11-10)

- "Por técnico" se filtra por escuadrilla: los técnicos se tildan al cerrar, pero los materiales son del cierre de la escuadrilla.

## Hecho

- `GET /admin/dashboard` (administración y dirección; el técnico recibe 403) devuelve todas las secciones con los mismos filtros: período (por defecto los últimos 30 días), cliente, escuadrilla, tipo de trabajo y tipo de equipo. Sin precios.
- Materiales más usados por cantidad, en los cierres del período, filtrable por escuadrilla y tipo de equipo. Sale de los materiales del cierre (E05-05), no del stock.
- **Gasto en materiales (2026-11-18, Gonza):** el tablero suma lo gastado en materiales en los cierres del período, con el precio de cada orden. Si la orden está aprobada usa el precio estampado; si no, el vigente de la lista (E04-08). Muestra el total y el ranking de materiales por importe. Los materiales sin precio, o con precio en cero, no suman y se avisan. Lo ven administración y dirección, igual que el resto del tablero; el técnico no tiene acceso.
