---
id: E04-10
title: "Registrar el cobro de una orden"
epic: E04
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-09]
blocked_by: []
assumes: []
---

# E04-10 Registrar el cobro de una orden

## Historia

**Como** administración, **quiero** registrar que una orden facturada fue cobrada, **para** cerrar el circuito y saber qué falta cobrar.

## Criterios de aceptación

1. **Dado:** una orden `Facturada`. **Cuando:** administración registra el cobro. **Entonces:** pasa a `Cobrada` y queda un registro de cobro con usuario y fecha.
2. **Dado:** una orden que no está `Facturada`. **Cuando:** se intenta registrar el cobro. **Entonces:** se rechaza.
3. **Dado:** una orden `Cobrada`. **Cuando:** se consulta. **Entonces:** es de solo lectura.
4. **Dado:** un cobro registrado por error. **Cuando:** administración lo anula. **Entonces:** queda auditado y la orden vuelve a `Facturada`.

## Decisiones (Gonza, 2026-11-10)

- Se registra fecha y medio de pago (efectivo, transferencia, cheque u otro). El importe es el total de la orden: no se carga.
- Anular un cobro pide motivo y la orden vuelve a Facturada; Cobrada deja de ser final solo para esto (R5).

## Hecho

- Tabla `work_order_payment` (un cobro vigente por orden; anularlo guarda quién, cuándo y por qué). `POST /admin/orders/{id}/payment` y `POST /admin/orders/{id}/payment/void`; transición nueva `void_payment` (Cobrada a Facturada).
- web-admin: "Registrar cobro" en Facturadas y "Anular cobro" en Cobradas.
