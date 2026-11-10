---
id: E12-05
title: "Paginación estándar en los listados"
epic: E12
phase: 1
priority: must
status: done
roles: [admin, owner]
size: S
areas: [backend, web-admin]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E12-05 Paginación estándar en los listados

## Historia

**Como** administración, **quiero** que todos los listados sean rápidos aunque haya miles de registros, **para** no sufrir límites como los de Power Apps con listas de SharePoint.

## Criterios de aceptación

1. **Dado:** un listado de la API. **Cuando:** se define. **Entonces:** está paginado con un tamaño máximo y orden estable.
2. **Dado:** miles de órdenes. **Cuando:** navego los listados. **Entonces:** cada página responde en menos de un segundo.
3. **Dado:** un listado nuevo sin paginación. **Cuando:** corre CI. **Entonces:** el test de rutas falla.

## Hecho

- `tests/test_route_pagination.py` recorre las rutas: todo GET que devuelve un arreglo sin paginar tiene que estar en la lista de excepciones con su motivo (catálogos y listas de un solo cliente), y toda página tiene `limit` con tope de 200 y `offset`.
