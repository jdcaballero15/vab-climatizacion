---
id: E03-09
title: "Pasar un equipo a otro cliente"
epic: E03
phase: 2
priority: should
status: draft
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-03]
blocked_by: []
assumes: [D-002]
---

# E03-09 Pasar un equipo a otro cliente

## Historia

**Como** administración, **quiero** pasar un equipo a otro cliente cuando lo venden o lo trasladan, **para** seguir atendiéndolo sin cargarlo de nuevo.

## Criterios de aceptación

1. **Dado:** un equipo de un cliente. **Cuando:** administración lo pasa a un domicilio activo de otro cliente. **Entonces:** el equipo queda en ese cliente y domicilio, y la ficha muestra de qué cliente vino y cuándo.
2. **Dado:** un equipo con trabajos hechos. **Cuando:** se lo pasa a otro cliente. **Entonces:** las órdenes anteriores siguen siendo del cliente original.
3. **Dado:** un domicilio inactivo o inexistente. **Cuando:** se intenta pasar el equipo ahí. **Entonces:** se rechaza con mensaje claro.

## Notas técnicas

- Respuesta del cliente (2026-10-28): un equipo puede pasar de un cliente a otro (venta o traslado).
- Hoy E03-03 solo permite mudar un equipo entre domicilios del mismo cliente.

## Preguntas abiertas

- ¿El cliente nuevo ve los trabajos que se le hicieron al equipo antes del traslado?
- ¿El equipo conserva su código o recibe uno nuevo con el número del cliente nuevo? (Ver D-002.)

## Fuera de alcance

- Unificar dos clientes: E03-08.
