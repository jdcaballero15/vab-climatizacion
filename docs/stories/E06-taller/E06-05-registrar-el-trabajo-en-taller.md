---
id: E06-05
title: "Registrar el trabajo en taller"
epic: E06
phase: 1
priority: must
status: done
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E06-04, E05-05]
blocked_by: []
assumes: []
---

# E06-05 Registrar el trabajo en taller

## Historia

**Como** técnico, **quiero** registrar el service o la reparación hecha en el taller con falla, reparación y repuestos, **para** que el trabajo quede en el historial del equipo.

## Criterios de aceptación

1. **Dado:** una etapa de taller asignada a mí. **Cuando:** la completo con falla, reparación y repuestos. **Entonces:** la etapa queda `done`.
2. **Dado:** los repuestos. **Cuando:** se registran. **Entonces:** se estampa el precio y se descuenta stock como en un cierre normal.
3. **Dado:** la etapa. **Cuando:** se completa. **Entonces:** no requiere firma del cliente.
4. **Dado:** el técnico. **Cuando:** ve la etapa. **Entonces:** no ve precios ni historial.

## Refinamiento y avance

Acordado con Gonza el 2026-11-03 (escuadrillas en todo, firma y nombre sin DNI, nace desde la visita y desde la oficina, PDF más adelante, etapas en fila: opción A del ADR 0007) y hecho el mismo día:

- "Trabajo en el galpón terminado" pide falla y reparación si el tipo de trabajo las pide, y estado del equipo; no se firma. Los materiales se cargan como en un cierre y el precio se estampa al aprobar (E05-05). El descuento de stock llega con E08-04. Vuelve a Pendiente con la etapa Devolución.
