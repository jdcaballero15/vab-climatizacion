---
id: E05-12
title: "Cierre de orden idempotente"
epic: E05
phase: 1
priority: must
status: in_progress
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

- Se implementa junto con E05-04 y E05-08 (un solo `POST /tech/orders/{id}/closure`). En el criterio 4, repuestos y stock se suman cuando llegue E05-05.
- La clave la genera la PWA (UUID) y se guarda en `work_order_closure.idempotency_key`. Permite reintentar el envío de un cierre si se corta la conexión (E05-13).

## Notas de implementación

- Se implementa con E05-04: ver sus notas de implementación.
