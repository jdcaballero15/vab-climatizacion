---
id: E04-06
title: "Detalle de la orden con línea de tiempo"
epic: E04
phase: 1
priority: must
status: done
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E04-01, E00-09]
blocked_by: []
assumes: []
---

# E04-06 Detalle de la orden con línea de tiempo

## Historia

**Como** administración, **quiero** ver el detalle completo de una orden con su línea de tiempo, **para** entender qué pasó, quién lo hizo y cuándo.

## Criterios de aceptación

1. **Dado:** una orden. **Cuando:** abro su detalle. **Entonces:** veo cliente, domicilio, equipo, tipo, técnico, estado y observaciones.
2. **Dado:** la línea de tiempo. **Cuando:** la consulto. **Entonces:** lista cada evento (creación, asignación, inicio, cierre, revisión, factura, cobro) con usuario y fecha.
3. **Dado:** una orden cerrada. **Cuando:** abro su detalle. **Entonces:** veo falla, reparación, repuestos usados con precio estampado, fotos y firma.
4. **Dado:** las fotos y la firma. **Cuando:** las abro. **Entonces:** se cargan con URLs firmadas de corta duración.

## Refinamiento y avance

Acordado con Gonza el 2026-11-03 y hecho el mismo día:

- `GET /admin/orders/{id}` (administración y dirección; técnico 403; 404 `order_not_found`): número, tipo, estado, fecha de creación (evento), cliente, domicilio con referencia, tipo de trabajo, equipo, indicaciones, canal, quién y dónde pidió, escuadrilla vigente con fecha prevista, cancelación, si tiene cierre y la línea de tiempo.
- Línea de tiempo: los eventos de la orden del más viejo al más nuevo, con el nombre de quién lo hizo y la nota. El cobro de E04-14 no deja evento propio: si está marcada Facturada, se suma un paso `billing_invoiced` con quién la marcó y el número de factura (fecha: la última edición del cobro). Cuando existan factura y cobro de verdad (E04-09, E04-10) van como eventos.
- Web-admin: pantalla `/ordenes/:id`, a la que se llega tocando el número en la tarjeta de Órdenes. Muestra los datos, el último cierre (con fotos y firma por URL firmada, criterios 3 y 4), los materiales con su precio (estampado si está aprobada) y la línea de tiempo.
- Dirección todavía no tiene Órdenes en su menú de web-admin; el endpoint ya se lo permite.
