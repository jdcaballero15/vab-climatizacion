---
id: E10-05
title: "Tablero: órdenes terminadas sin facturar"
epic: E10
phase: 1
priority: must
status: done
roles: [owner, admin]
size: S
areas: [backend, web-admin]
depends_on: [E10-01, E04-09]
blocked_by: []
assumes: []
---

# E10-05 Tablero: órdenes terminadas sin facturar

## Historia

**Como** dirección, **quiero** ver las órdenes terminadas que todavía no se facturaron, **para** que ningún trabajo quede sin cobrar.

## Criterios de aceptación

1. **Dado:** órdenes `Terminada` sin factura. **Cuando:** abro la sección. **Entonces:** veo cliente, orden, fecha de cierre y días transcurridos.
2. **Dado:** la lista. **Cuando:** se ordena por antigüedad. **Entonces:** las más viejas aparecen primero.
3. **Dado:** una orden que se factura. **Cuando:** se registra la factura. **Entonces:** desaparece de la lista.

## Hecho

- `GET /admin/dashboard` (administración y dirección; el técnico recibe 403) devuelve todas las secciones con los mismos filtros: período (por defecto los últimos 30 días), cliente, escuadrilla, tipo de trabajo y tipo de equipo. Sin precios.
- Terminadas sin facturar, la más vieja primero, con cliente, número, fecha de cierre y días; no dependen del período. Al facturarse pasan a Facturada y salen de la lista.
