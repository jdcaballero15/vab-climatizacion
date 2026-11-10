---
id: E08-03
title: "Transferir repuestos entre ubicaciones"
epic: E08
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E08-02]
blocked_by: []
assumes: []
---

# E08-03 Transferir repuestos entre ubicaciones

## Historia

**Como** administración, **quiero** transferir repuestos del depósito a una camioneta, o entre ubicaciones, **para** que cada técnico salga con lo que necesita.

## Criterios de aceptación

1. **Dado:** una transferencia con origen, destino, repuesto y cantidad. **Cuando:** se registra. **Entonces:** se resta de origen y se suma en destino en una sola transacción.
2. **Dado:** una cantidad mayor al stock del origen. **Cuando:** se intenta transferir. **Entonces:** se rechaza.
3. **Dado:** origen y destino iguales. **Cuando:** se intenta. **Entonces:** se rechaza.

## Hecho

- `POST /admin/stock/transfers`: un solo movimiento `transfer` (sale del origen y entra al destino). Bloquea el origen para que dos transferencias a la vez no lo dejen en negativo; más de lo que hay da 409 con lo disponible; mismo origen y destino, 422.
