---
id: E04-08
title: "Revisar una orden terminada"
epic: E04
phase: 1
priority: must
status: in_progress
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
