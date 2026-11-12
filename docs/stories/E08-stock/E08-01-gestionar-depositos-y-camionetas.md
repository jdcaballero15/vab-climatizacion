---
id: E08-01
title: "Gestionar depósitos y camionetas"
epic: E08
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E01-04]
blocked_by: []
assumes: []
---

# E08-01 Gestionar depósitos y camionetas

## Historia

**Como** administración, **quiero** dar de alta los depósitos y las camionetas (con su escuadrilla), **para** saber dónde está cada repuesto.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un depósito o una camioneta con nombre. **Entonces:** queda disponible como ubicación de stock.
2. **Dado:** una camioneta. **Cuando:** se asocia a una escuadrilla. **Entonces:** los usos de repuestos de esa escuadrilla descuentan de esa camioneta.
3. **Dado:** una ubicación con movimientos. **Cuando:** se quiere eliminar. **Entonces:** solo se puede desactivar.

## Decisiones (Gonza, 2026-11-10)

- Los depósitos los carga la oficina (no hay lista inicial). Cada escuadrilla tiene su camioneta como ubicación: la camioneta lleva la escuadrilla.

## Hecho

- Tabla `stock_location` (depósito o camioneta; la camioneta con `crew_id`, una activa por escuadrilla). `GET/POST /admin/stock/locations`, `PATCH /admin/stock/locations/{id}` para renombrar, cambiar la escuadrilla o desactivar; no se borran.
- web-admin: sección "Depósitos y camionetas" en la pantalla Stock.
