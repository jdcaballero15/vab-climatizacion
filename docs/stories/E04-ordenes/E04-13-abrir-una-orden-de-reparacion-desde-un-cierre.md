---
id: E04-13
title: "Abrir una orden de reparación desde un cierre"
epic: E04
phase: 2
priority: should
status: draft
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-02, E04-08]
blocked_by: []
assumes: []
---

# E04-13 Abrir una orden de reparación desde un cierre

## Historia

**Como** administración, **quiero** abrir una orden de reparación a partir de lo que la escuadrilla anotó al cerrar un service, **para** no perder una falla que apareció en la rutina.

## Criterios de aceptación

1. **Dado:** una orden `Terminada` con observación. **Cuando:** administración elige "Abrir orden de reparación". **Entonces:** se abre el alta de orden con el cliente, el domicilio y el equipo de la orden original, y la observación como descripción, para revisar antes de guardar.
2. **Dado:** la orden nueva guardada. **Cuando:** administración consulta cualquiera de las dos. **Entonces:** ve la relación entre ambas.

## Notas técnicas

- Respuesta del cliente (2026-10-28): en el service no se pide falla y reparación (E02-10), pero tiene que haber una observación para anotar una falla y poder generar una orden de correctivo. La observación del cierre ya existe (E05-04); falta el atajo para abrir la orden.

- Decidido (Gonza lo dejó a recomendación, 2026-10-28): sirve desde **cualquier tipo de trabajo** Terminado con observación, no solo el service; una falla puede aparecer en cualquier visita y no agrega reglas por tipo. La escuadrilla no marca nada nuevo en el cierre: la oficina lee la observación al revisar la Terminada (E04-08). Si después hace falta un aviso explícito, se suma.

## Fuera de alcance

- Que la escuadrilla abra la orden desde el celular.
