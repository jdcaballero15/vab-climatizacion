---
id: E06-08
title: "Estado calculado y facturación única de la orden de taller"
epic: E06
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend]
depends_on: [E06-06, E04-08]
blocked_by: []
assumes: []
---

# E06-08 Estado calculado y facturación única de la orden de taller

## Historia

**Como** administración, **quiero** que el estado de una orden de taller se calcule solo según sus etapas, **para** no tener que mantenerlo a mano ni facturar tres veces.

## Criterios de aceptación

1. **Dado:** las etapas de una orden. **Cuando:** cambian. **Entonces:** el estado de la orden se recalcula según la tabla de `order-state-machine.md`.
2. **Dado:** una orden de taller con la devolución terminada. **Cuando:** administración la revisa y factura. **Entonces:** se genera un único registro de factura.
3. **Dado:** un intento de facturar una etapa por separado. **Cuando:** se realiza. **Entonces:** se rechaza.

## Refinamiento y avance

Acordado con Gonza el 2026-11-03 (escuadrillas en todo, firma y nombre sin DNI, nace desde la visita y desde la oficina, PDF más adelante, etapas en fila: opción A del ADR 0007) y hecho el mismo día:

- Con la opción A el estado no se calcula: lo dejan los cierres de cada etapa (tabla en `order-state-machine.md`). Se factura una sola vez, al quedar Terminada (E04-14); no hay facturación por etapa.
