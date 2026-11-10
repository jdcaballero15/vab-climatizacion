---
id: E03-07
title: "Baja lógica y restauración de clientes y equipos"
epic: E03
phase: 1
priority: should
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E03-01, E03-03]
blocked_by: []
assumes: []
---

# E03-07 Baja lógica y restauración de clientes y equipos

## Historia

**Como** administración, **quiero** dar de baja y restaurar clientes y equipos, **para** corregir errores sin perder información.

## Criterios de aceptación

1. **Dado:** un cliente o equipo. **Cuando:** administración lo da de baja. **Entonces:** deja de ofrecerse para órdenes nuevas y conserva todo su historial.
2. **Dado:** un registro dado de baja. **Cuando:** administración lo restaura. **Entonces:** vuelve a estar disponible.
3. **Dado:** una baja o restauración. **Cuando:** se realiza. **Entonces:** queda en la auditoría.
4. **Dado:** un cliente con órdenes abiertas. **Cuando:** se intenta dar de baja. **Entonces:** el sistema lo impide e indica las órdenes.

## Decisiones (Gonza, 2026-11-10)

- La baja es borrado lógico (`deleted_at`), igual para clientes y equipos. Un equipo en órdenes abiertas tampoco se da de baja.

## Hecho

- `POST /admin/clients/{id}/deactivation` y `/restoration`; `POST /admin/equipment/{id}/deactivation` y `/restoration`. Con órdenes abiertas, 409 con los números.
- Los dados de baja se listan con `?deleted=true` (clientes y equipos de un cliente). La ficha y el historial del cliente dado de baja se siguen leyendo; no se le crean órdenes ni equipos.
- Cada baja y restauración queda en `audit_event` (tabla nueva, base de E12-01); la del cliente se ve en `GET /admin/clients/{id}/audit`.
- web-admin: "Dar de baja" y "Restaurar" en la ficha del cliente y en cada equipo, y la casilla "Ver dados de baja" en las dos listas.
