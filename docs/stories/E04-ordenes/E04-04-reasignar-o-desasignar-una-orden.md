---
id: E04-04
title: "Reasignar o desasignar una orden"
epic: E04
phase: 1
priority: must
status: draft
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-03]
blocked_by: []
assumes: []
---

# E04-04 Reasignar o desasignar una orden

## Historia

**Como** administración, **quiero** cambiar la escuadrilla de una orden o quitarle la asignación, **para** reorganizar el trabajo cuando cambia el plan del día.

## Criterios de aceptación

1. **Dado:** una orden `Asignada`. **Cuando:** administración la reasigna a otra escuadrilla. **Entonces:** la escuadrilla anterior deja de verla y la nueva la ve.
2. **Dado:** una orden `Asignada`. **Cuando:** administración la desasigna. **Entonces:** vuelve a `Pendiente`.
3. **Dado:** una orden `En curso`. **Cuando:** administración la reasigna. **Entonces:** se pide confirmación y lo ya registrado se conserva.
4. **Dado:** cada cambio. **Cuando:** se realiza. **Entonces:** queda un evento con motivo opcional.

## Notas técnicas

- Sin modo offline (ADR 0009) no hay datos sin sincronizar. Si la escuadrilla anterior tenía un cierre pendiente de enviar, el servidor lo rechaza (ver E05-13).
- Por D-013 la orden se asigna a una escuadrilla, no a un técnico.
