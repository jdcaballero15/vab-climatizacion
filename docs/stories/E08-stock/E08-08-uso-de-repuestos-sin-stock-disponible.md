---
id: E08-08
title: "Uso de repuestos sin stock disponible"
epic: E08
phase: 1
priority: should
status: done
roles: [technician, admin]
size: S
areas: [backend, web-admin]
depends_on: [E08-04, E08-06]
blocked_by: []
assumes: []
---

# E08-08 Uso de repuestos sin stock disponible

## Historia

**Como** técnico, **quiero** poder registrar un repuesto aunque el sistema crea que no hay stock, **para** no frenar el cierre de un trabajo por un error de inventario.

## Criterios de aceptación

1. **Dado:** un cierre con un repuesto sin stock suficiente en la camioneta. **Cuando:** se procesa. **Entonces:** se acepta y la camioneta queda con saldo negativo marcado para ajuste.
2. **Dado:** un saldo negativo. **Cuando:** administración abre el stock. **Entonces:** se destaca para corregirlo.
3. **Dado:** un técnico. **Cuando:** recibe el resultado del cierre. **Entonces:** no se lo bloquea ni se le muestra un error.

## Decisiones (Gonza, 2026-11-10)

- Se permite y se marca: el cierre no se bloquea ni muestra error, la camioneta queda en negativo y la oficina la ve destacada para ajustarla.

## Hecho

- El uso no valida stock. `StockPartOut.has_negative` marca el repuesto con alguna ubicación en negativo; web-admin lo resalta con "Saldo negativo: ajustar".
