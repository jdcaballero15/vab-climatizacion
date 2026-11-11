---
id: E04-05
title: "Panel de órdenes por estado"
epic: E04
phase: 1
priority: must
status: done
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E04-01]
blocked_by: []
assumes: []
---

# E04-05 Panel de órdenes por estado

## Historia

**Como** administración, **quiero** ver un panel con las órdenes por estado: pendientes, en curso, terminadas sin facturar, facturadas y cobradas, **para** seguir el trabajo de un vistazo y no dejar nada sin cobrar.

## Criterios de aceptación

1. **Dado:** órdenes en varios estados. **Cuando:** abro el panel. **Entonces:** veo columnas o pestañas por estado con la cantidad de cada una.
2. **Dado:** el panel. **Cuando:** filtro por escuadrilla, cliente, tipo de trabajo o período. **Entonces:** la lista y los totales se actualizan.
3. **Dado:** miles de órdenes. **Cuando:** navego. **Entonces:** la lista está paginada y responde en menos de un segundo.
4. **Dado:** una orden terminada hace más de un día sin facturar. **Cuando:** abro el panel. **Entonces:** se destaca como "terminada sin facturar".
5. **Dado:** dirección. **Cuando:** abre el panel. **Entonces:** ve lo mismo en modo lectura.

## Decisiones (Gonza, 2026-11-10)

- Umbral de demora: 7 días desde el cierre, configurable con `BILLING_OVERDUE_DAYS` (el criterio 4 decía un día).
- El período filtra por fecha de creación de la orden; la escuadrilla es la de la última asignación.

## Hecho

- `GET /admin/orders` lista los siete estados (suma `invoiced` y `paid`) con filtros `crew_id`, `client_id`, `work_type_id`, `created_from` y `created_to`; cada ítem trae `billing_overdue`. Admin y dirección.
- Dirección (`owner`) ve Órdenes y el detalle en modo lectura: sin alta, sin acciones, sin editar materiales ni importes. Para los filtros puede leer las listas de escuadrillas, tipos de trabajo y clientes.
- web-admin: pestañas Facturadas y Cobradas, cifras con los filtros aplicados, barra de filtros y la marca "Terminada sin facturar hace más de una semana".
