---
id: E08-07
title: "Ver el historial de movimientos de un repuesto"
epic: E08
phase: 1
priority: should
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E08-04]
blocked_by: []
assumes: []
---

# E08-07 Ver el historial de movimientos de un repuesto

## Historia

**Como** administración, **quiero** ver todos los movimientos de un repuesto (ingresos, transferencias, usos y ajustes), **para** entender cómo llegó el stock al valor actual.

## Criterios de aceptación

1. **Dado:** un repuesto. **Cuando:** abro su historial. **Entonces:** veo cada movimiento con fecha, tipo, cantidad, origen, destino, usuario y orden asociada.
2. **Dado:** un uso en una orden. **Cuando:** lo veo. **Entonces:** puedo ir a esa orden.
3. **Dado:** el rol técnico. **Cuando:** intenta acceder. **Entonces:** recibe acceso denegado.

## Hecho

- `GET /admin/stock/parts/{id}/movements`: todos los movimientos del repuesto con fecha, tipo, cantidad, origen, destino, usuario, motivo y orden. El técnico recibe 403.
- web-admin: "Historial" en cada repuesto, con link a la orden de cada uso.
