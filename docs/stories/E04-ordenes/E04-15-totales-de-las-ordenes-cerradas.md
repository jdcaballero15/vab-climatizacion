---
id: E04-15
title: "Totales de las órdenes cerradas"
epic: E04
phase: 1
priority: should
status: done
roles: [admin, owner]
size: S
areas: [backend, web-admin]
depends_on: [E04-05, E04-14]
blocked_by: []
assumes: []
---

# E04-15 Totales de las órdenes cerradas

## Historia

**Como** administración o dirección, **quiero** ver cuántas órdenes hay y cuánto suman cuando miro las terminadas, facturadas o cobradas, **para** saber de un vistazo cuánto falta facturar, cuánto se facturó y cuánto se cobró.

## Criterios de aceptación

1. **Dado:** órdenes cobradas con importes. **Cuando:** abro Órdenes en la pestaña Cobradas. **Entonces:** arriba de la lista veo la cantidad de órdenes y la suma de sus totales.
2. **Dado:** la pestaña Terminadas o Facturadas. **Cuando:** la abro. **Entonces:** veo lo mismo para ese estado.
3. **Dado:** filtros por escuadrilla, cliente, tipo de trabajo o período. **Cuando:** los aplico. **Entonces:** la cantidad y la suma son las de las órdenes filtradas, de todas las páginas y no solo de la que se ve.
4. **Dado:** el total de cada orden. **Cuando:** se suma. **Entonces:** se usa el mismo total que muestra la orden: materiales (precio estampado si está aprobada, si no el vigente), mano de obra y otros cargos.
5. **Dado:** las pestañas de órdenes abiertas o canceladas. **Cuando:** las abro. **Entonces:** no se muestra suma de importes.
6. **Dado:** un técnico. **Cuando:** pide el listado. **Entonces:** el sistema lo rechaza (el listado ya es solo de administración y dirección).

## Notas técnicas

- Pedido de Agus (2026-11-24): "si se puede hacer una cuantificación de totales de esas órdenes".
- `GET /admin/orders` suma `amount_total` cuando el estado es `done`, `invoiced` o `paid`; nulo en los demás.
- El total de materiales se calcula para todas las órdenes juntas (no una consulta por orden), así el listado sigue respondiendo rápido con muchas órdenes.

## Hecho

- `GET /admin/orders` devuelve `amount_total` en `done`, `invoiced` y `paid` (nulo en el resto): la suma de `billing.total` de todas las órdenes del filtro, sin paginar (`WorkOrderRepository.ids_by_status`, `billing.amount_total`).
- `order_materials.materials_totals` calcula los materiales de muchas órdenes con tres consultas; `billing_by_order` lo usa también para el listado, que antes hacía una consulta por orden.
- web-admin: junto a "N en total" se ve la suma en pesos, con los filtros aplicados.

## Fuera de alcance

- Sumas por escuadrilla o por cliente dentro de la misma pestaña: para eso está el tablero.
