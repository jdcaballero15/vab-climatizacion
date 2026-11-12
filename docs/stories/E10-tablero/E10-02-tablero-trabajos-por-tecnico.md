---
id: E10-02
title: "Tablero: trabajos por técnico"
epic: E10
phase: 1
priority: must
status: done
roles: [owner, admin]
size: S
areas: [backend, web-admin]
depends_on: [E10-01, E05-04]
blocked_by: []
assumes: []
---

# E10-02 Tablero: trabajos por técnico

## Historia

**Como** dirección, **quiero** ver cuántos trabajos hizo cada técnico en el período, **para** repartir mejor la carga.

## Criterios de aceptación

1. **Dado:** un período. **Cuando:** lo elijo. **Entonces:** veo por técnico las órdenes cerradas en las que fue (según lo tildado al cerrar, D-013) y, por escuadrilla, las que tiene en curso.
2. **Dado:** el tablero. **Cuando:** lo consulta un técnico. **Entonces:** recibe acceso denegado.

## Notas técnicas

- Por D-013 los técnicos no tienen usuario: el conteo por persona sale de `work_order_closure_technician`; lo que está en curso se cuenta por escuadrilla.

## Hecho

- `GET /admin/dashboard` (administración y dirección; el técnico recibe 403) devuelve todas las secciones con los mismos filtros: período (por defecto los últimos 30 días), cliente, escuadrilla, tipo de trabajo y tipo de equipo. Sin precios.
- Por técnico: los cierres del período en los que fue tildado (D-013). Por escuadrilla: lo asignado o en curso ahora.
