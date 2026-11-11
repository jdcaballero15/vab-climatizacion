---
id: E08-02
title: "Registrar el ingreso de repuestos"
epic: E08
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E08-01, E02-05]
blocked_by: []
assumes: []
---

# E08-02 Registrar el ingreso de repuestos

## Historia

**Como** administración, **quiero** registrar el ingreso de repuestos al depósito, **para** mantener el stock al día.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** registra un ingreso con repuesto, cantidad y depósito. **Entonces:** se agrega un movimiento `receipt` y el stock del depósito aumenta.
2. **Dado:** una cantidad cero o negativa. **Cuando:** se intenta registrar. **Entonces:** se rechaza.
3. **Dado:** un ingreso. **Cuando:** se registra. **Entonces:** queda con usuario y fecha.

## Hecho

- `POST /admin/stock/receipts`: movimiento `receipt` con usuario y fecha. Cantidad mayor que cero, hasta tres decimales (422 si no).
