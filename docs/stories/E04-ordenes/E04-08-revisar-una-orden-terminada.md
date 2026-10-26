---
id: E04-08
title: "Revisar una orden terminada"
epic: E04
phase: 1
priority: must
status: draft
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
