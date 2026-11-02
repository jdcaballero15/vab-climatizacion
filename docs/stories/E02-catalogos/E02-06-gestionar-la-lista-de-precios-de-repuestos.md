---
id: E02-06
title: "Gestionar la lista de precios de repuestos"
epic: E02
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E02-05]
blocked_by: []
assumes: []
---

# E02-06 Gestionar la lista de precios de repuestos

## Historia

**Como** administración, **quiero** cargar y actualizar el precio de lista de cada material conservando el historial, **para** calcular el precio de cada orden sin perder los precios con que se cobró antes.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** actualiza el precio de un material. **Entonces:** se agrega un precio nuevo con fecha de vigencia y quién lo cargó, y el anterior se conserva.
2. **Dado:** un precio actualizado. **Cuando:** hay órdenes ya aprobadas con ese material. **Entonces:** esas órdenes mantienen el precio estampado al aprobarlas (E05-05).
3. **Dado:** el rol técnico. **Cuando:** consulta cualquier recurso de materiales. **Entonces:** ningún campo de precio está en la respuesta.
4. **Dado:** un precio negativo o con más de dos decimales. **Cuando:** se guarda. **Entonces:** se rechaza.

## Decisiones tomadas en el refinamiento

Validadas con Gonza el 2026-11-02:

- **El precio de una orden queda congelado al aprobarla**, no cuando la escuadrilla usa el material. Como los precios arrancan en $0, si se congelara al cerrar, las órdenes de los primeros días quedarían en $0 para siempre. Hasta aprobarla, la orden toma el precio vigente de la lista.
- El registro en la auditoría general (E12-01) se reemplaza, por ahora, por el historial de `part_price` (cada fila tiene fecha y `created_by`).

## Notas técnicas

- Tabla `part_price` (`list_price NUMERIC(14,2)` con CHECK `>= 0`, `valid_from`, `created_by`). Nunca se edita una fila: el vigente es el último por `valid_from`. Migración `63b8f5e979d4`.
- `PUT /admin/parts/{id}/price` con `{list_price}` agrega la fila. `PartAdminOut` trae `list_price` y `price_updated_at` vigentes. Solo administración.
- web-admin: el precio se edita en la fila de la hoja "Materiales y precios" (acepta coma o punto) y muestra la fecha de la última actualización.
- El estampado en la orden y la aprobación llegan con E05-05.
