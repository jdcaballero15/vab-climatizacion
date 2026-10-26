---
id: E04-12
title: "Asociar un equipo a la orden"
epic: E04
phase: 1
priority: must
status: draft
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-02, E03-03]
blocked_by: []
assumes: [D-002]
---

# E04-12 Asociar un equipo a la orden

## Historia

**Como** administración, **quiero** elegir sobre qué equipo del cliente se hará el trabajo, **para** que cada trabajo quede en el historial del equipo.

## Criterios de aceptación

1. **Dado:** una orden de un cliente con equipos. **Cuando:** elijo el equipo. **Entonces:** solo se ofrecen los equipos del domicilio y cliente elegidos.
2. **Dado:** un tipo de trabajo que no requiere equipo. **Cuando:** creo la orden. **Entonces:** el equipo es opcional.
3. **Dado:** una orden con equipo. **Cuando:** se cierra. **Entonces:** el trabajo aparece en la ficha del equipo.
