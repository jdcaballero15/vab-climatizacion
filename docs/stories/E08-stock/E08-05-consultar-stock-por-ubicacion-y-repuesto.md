---
id: E08-05
title: "Consultar stock por ubicación y repuesto"
epic: E08
phase: 1
priority: must
status: done
roles: [admin, technician, owner]
size: S
areas: [backend, web-admin, pwa]
depends_on: [E08-04]
blocked_by: []
assumes: []
---

# E08-05 Consultar stock por ubicación y repuesto

## Historia

**Como** administración, **quiero** consultar cuánto hay de cada repuesto en cada depósito y camioneta, **para** decidir qué reponer y qué transferir.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** abre la consulta de stock. **Entonces:** ve cada repuesto con su cantidad por ubicación y el total.
2. **Dado:** un técnico. **Cuando:** consulta el stock. **Entonces:** solo ve el de su camioneta.
3. **Dado:** la consulta. **Cuando:** se filtra por repuesto o ubicación. **Entonces:** se actualiza.
4. **Dado:** el stock. **Cuando:** se calcula. **Entonces:** es la suma de movimientos y coincide con el historial.

## Hecho

- `GET /admin/stock` (administración y dirección): cada repuesto con su cantidad por ubicación y el total, filtrable por repuesto y ubicación. Es la suma de los movimientos.
- web-admin: pantalla Stock (menú de administración).
