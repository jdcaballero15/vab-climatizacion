---
id: E08-04
title: "Descontar stock al usar repuestos en un cierre"
epic: E08
phase: 1
priority: must
status: done
roles: [technician]
size: M
areas: [backend]
depends_on: [E08-03, E05-12, E02-06]
blocked_by: []
assumes: []
---

# E08-04 Descontar stock al usar repuestos en un cierre

## Historia

**Como** técnico, **quiero** que al cerrar una orden con repuestos se descuente el stock de mi camioneta, **para** no tener que cargar el consumo dos veces.

## Criterios de aceptación

1. **Dado:** un cierre con repuestos. **Cuando:** el servidor lo procesa. **Entonces:** crea un movimiento `usage` por repuesto desde la camioneta del técnico, en la misma transacción que el cierre.
2. **Dado:** un cierre. **Cuando:** se procesa dos veces por un reintento. **Entonces:** el stock se descuenta una sola vez (idempotencia).
3. **Dado:** un uso de repuesto. **Cuando:** se registra. **Entonces:** guarda el precio de lista vigente como precio estampado.
4. **Dado:** el técnico. **Cuando:** consulta su stock. **Entonces:** ve cantidades de su camioneta y no ve precios.

## Decisiones (Gonza, 2026-11-10)

- Lo usado sale de la camioneta de la escuadrilla que cierra. Sin camioneta cargada, el cierre funciona igual y no mueve stock. Los materiales "Otro" escritos a mano no mueven stock.
- El precio sigue estampándose al aprobar la orden (regla 4 de CLAUDE.md, E05-05), no al cerrar: el criterio 3 queda así.

## Hecho

- El cierre (`POST /tech/orders/{id}/closure`) crea un movimiento `usage` por material de la lista, en la misma transacción. `stock_movement.part_usage_id` es único: un reenvío del cierre no descuenta dos veces.
- `GET /tech/stock`: la camioneta de la escuadrilla con cantidades, sin precios. PWA: botón "Mi camioneta" en Mis órdenes.
- Si la oficina corrige los materiales de una orden después del cierre, el stock no se corrige solo: se ajusta (E08-06).
