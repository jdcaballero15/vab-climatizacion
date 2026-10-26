---
id: E05-12
title: "Cierre de orden idempotente"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: S
areas: [backend]
depends_on: [E05-04, E04-01]
blocked_by: []
assumes: []
---

# E05-12 Cierre de orden idempotente

## Historia

**Como** técnico, **quiero** que enviar un cierre dos veces no lo duplique, **para** no tener órdenes cerradas dos veces por un reintento.

## Criterios de aceptación

1. **Dado:** un cierre con clave de idempotencia nueva. **Cuando:** el servidor lo procesa. **Entonces:** se crea una sola vez.
2. **Dado:** el mismo cierre con la misma clave. **Cuando:** se vuelve a enviar. **Entonces:** el servidor devuelve el resultado original sin repetir efectos (stock, eventos).
3. **Dado:** dos cierres distintos de la misma orden. **Cuando:** llegan con claves distintas. **Entonces:** el segundo se rechaza si la orden ya no está `En curso`.
4. **Dado:** un cierre. **Cuando:** se procesa. **Entonces:** ocurre en una sola transacción (cierre, repuestos, stock, evento).

## Notas técnicas

- La clave la genera la PWA (UUID) y se guarda en `work_order_closure.idempotency_key`. Permite reintentar el envío de un cierre si se corta la conexión (E05-13).
