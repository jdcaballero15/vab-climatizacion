---
id: E03-05
title: "Ficha de equipo con historial y mediciones"
epic: E03
phase: 1
priority: must
status: done
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E03-03, E04-06]
blocked_by: []
assumes: [D-002]
---

# E03-05 Ficha de equipo con historial y mediciones

## Historia

**Como** administración, **quiero** ver la ficha de un equipo con su historial de trabajos, repuestos y mediciones, **para** saber qué se le hizo y detectar si viene fallando.

## Criterios de aceptación

1. **Dado:** un equipo con trabajos. **Cuando:** abro su ficha. **Entonces:** veo trabajos anteriores, repuestos usados y mantenimientos y reparaciones previos.
2. **Dado:** un equipo con mediciones de mantenimiento. **Cuando:** abro su ficha. **Entonces:** veo la evolución de cada medición (ver E99-12). *Fuera: mediciones al icebox.*
3. **Dado:** un equipo migrado desde Persat. **Cuando:** abro su ficha. **Entonces:** su historial importado se distingue del generado en el sistema nuevo.
4. **Dado:** el rol técnico. **Cuando:** intenta acceder. **Entonces:** recibe acceso denegado.

## Decisiones (Gonza, 2026-11-10)

- Sin mediciones: el criterio 2 queda fuera porque las mediciones pasaron al icebox (E99-09, E99-11 y E99-12).

## Hecho

- `GET /admin/equipment/{id}/file` (administración y dirección; el técnico recibe 403): datos, traslados y trabajos del equipo, el más nuevo primero, con falla, reparación, observación y materiales sin precios. Cada trabajo marca `before_transfer` (de otro cliente, anterior al traslado) e `imported` (tiene referencia de Persat, `legacy_reference` con `entity = work_order`).
- También funciona para un equipo dado de baja.
- web-admin: página `/equipos/:id`, con link "Ficha" desde la lista de equipos del cliente.
