---
id: E05-01
title: "Ver mis órdenes asignadas"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: S
areas: [backend, pwa]
depends_on: [E04-03, E01-04, E00-03]
blocked_by: []
assumes: []
---

# E05-01 Ver mis órdenes asignadas

## Historia

**Como** escuadrilla, **quiero** ver en el celular la lista de las órdenes asignadas a mi escuadrilla con cliente, dirección, equipo y tarea, **para** saber a dónde ir y qué hacer.

## Criterios de aceptación

1. **Dado:** el usuario de una escuadrilla con órdenes asignadas. **Cuando:** abre la app. **Entonces:** ve solo las órdenes `Asignada` y `En curso` de su escuadrilla, ordenadas por fecha prevista.
2. **Dado:** una orden reasignada a otra escuadrilla o cancelada. **Cuando:** la escuadrilla actualiza la lista. **Entonces:** deja de verla.
3. **Dado:** la respuesta de la API. **Cuando:** se la inspecciona. **Entonces:** no contiene precios, mano de obra ni historial de clientes.
4. **Dado:** una escuadrilla sin órdenes. **Cuando:** abre la app. **Entonces:** ve un mensaje claro de que no tiene trabajo asignado.

## Notas técnicas

- Endpoint `/tech/orders`. Esquema `OrderTechnicianOut`. Cubierto por el test de contrato E00-04.
- Por D-013 el usuario de la app es el de la escuadrilla (un usuario por celular). Antes de pasar a `ready`, revisar la lista del prototipo del cliente (código, tipo, estado, título, cliente, fecha relativa, dirección; pestañas "Para hacer" y "Hechas esta semana").
