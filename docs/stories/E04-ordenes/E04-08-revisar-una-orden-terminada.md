---
id: E04-08
title: "Revisar una orden terminada"
epic: E04
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E04-06]
blocked_by: []
assumes: [D-005]
---

# E04-08 Revisar una orden terminada

## Historia

**Como** administración, **quiero** revisar cada orden terminada antes de facturar y poder aprobarla o devolverla a la escuadrilla, **para** no facturar trabajos con datos incompletos o dudosos.

## Criterios de aceptación

1. **Dado:** una orden `Terminada`. **Cuando:** administración la revisa. **Entonces:** ve todo lo cargado por la escuadrilla en una sola pantalla, incluido quiénes fueron.
2. **Dado:** una orden `Terminada` en revisión. **Cuando:** administración la aprueba. **Entonces:** queda marcada como revisada (evento) y habilitada para facturar.
3. **Dado:** una orden `Terminada` en revisión. **Cuando:** administración la devuelve con un motivo. **Entonces:** vuelve a `Asignada` a la misma escuadrilla con el motivo visible.
4. **Dado:** una orden `Terminada` sin revisar. **Cuando:** se intenta facturar. **Entonces:** se rechaza.
5. **Dado:** una medición fuera de rango o una observación en "Otro". **Cuando:** se revisa. **Entonces:** se destaca para que no pase inadvertida.

## Notas técnicas

- Según `D-005`, la revisión es una acción (evento `review_approved` o `review_returned`) y no un estado nuevo.

## Avance

Hecho el 2026-10-28, para que administración vea las terminadas en la prueba del cliente del 2026-10-30 (decisión de Gonza):

- **Criterio 1, en su versión mínima.** `GET /admin/orders?status=done` lista las terminadas (la última cerrada primero) con escuadrilla y fecha de cierre (`completed`). `GET /admin/orders/{id}/closure` devuelve el último cierre con nombres: resultado, quién y cuándo cerró, escuadrilla, técnicos que fueron, tareas, falla y reparación (catálogo o texto de "Otro"), estado del equipo, motivo y observación. 404 si la orden no existe o no tiene cierre; solo administración.
- Web-admin: "Terminadas" en el selector de estado de Órdenes, con "Ver cierre" que despliega el detalle debajo de la fila. Sin acción de cancelar (R3).
- Falta: aprobar y devolver (criterios 2 y 3), bloquear la factura sin revisión (criterio 4), destacar mediciones y "Otro" (criterio 5), fotos y firma (con E00-09) y la pantalla de detalle de E04-06.

Hecho el 2026-11-02 con E05-05 (materiales en la orden):

- **Criterio 2, aprobar:** `POST /admin/orders/{id}/approval` registra `review_approved` (sin cambio de estado) y estampa el precio de los materiales. Solo desde `Terminada`, una sola vez y sin materiales "Otro" pendientes. En web-admin, "Aprobar orden" en la sección Materiales.
- **Criterio 4, en la versión mínima de cobro (E04-14):** marcar "Facturada" exige la orden aprobada (409 `order_not_approved`).
- Falta: devolver a la escuadrilla (criterio 3), destacar mediciones y "Otro" de falla y reparación (criterio 5) y la pantalla de detalle de E04-06. Cuando exista devolver, tiene que volver a habilitar la edición de materiales.

Hecho el 2026-11-03:

- **Criterio 3, devolver:** `POST /admin/orders/{id}/return` con `reason` (obligatorio, hasta 500 caracteres) y `scheduled_for` (de hoy en adelante; en web-admin, hoy por defecto). Vuelve a `Asignada` a la escuadrilla de la asignación vigente, que es la que la cerró (R8), con evento `review_returned` y el motivo. El motivo queda en `work_order_assignment.return_reason` (migración `33e9362dae73`): la escuadrilla lo ve en la tarjeta y en el detalle del celular, y la oficina en Asignadas, mientras esa asignación siga vigente (una reasignación no lo arrastra). 409 `order_approved` si ya está aprobada (decisión de Gonza: los precios ya están estampados), 409 `order_invoiced` si ya está marcada Facturada (las de antes de E05-05 pueden estar facturadas sin aprobar), 409 `invalid_transition` si no está `Terminada`, 422 `crew_not_available` si la escuadrilla se desactivó (se reasigna después de devolverla a otra). La fila de la orden se bloquea como al aprobar, para que aprobar y devolver no se crucen. Los materiales se vuelven a editar porque la orden deja de estar cerrada.
- **Criterio 5, "Otro":** `GET /admin/orders/{id}/closure` suma `failure_is_other` y `repair_is_other`; web-admin destaca esas filas con la etiqueta "Otro". Las mediciones fuera de rango se destacan con E07-07, cuando existan las mediciones.
- Fuera de esta historia: la pantalla de detalle con la línea de tiempo (E04-06).
