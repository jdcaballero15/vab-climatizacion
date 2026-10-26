---
id: E04-02
title: "Crear una orden de trabajo"
epic: E04
phase: 1
priority: must
status: draft
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E04-01, E03-02, E02-01]
blocked_by: []
assumes: []
---

# E04-02 Crear una orden de trabajo

## Historia

**Como** administración, **quiero** crear una orden de trabajo a partir de un pedido de un cliente (llega por WhatsApp o mail), **para** que el pedido quede registrado y no se pierda.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea una orden con cliente, domicilio, tipo de trabajo y descripción. **Entonces:** queda en estado `Pendiente` con un número correlativo legible.
2. **Dado:** una orden recién creada. **Cuando:** se guarda. **Entonces:** queda un evento de creación con usuario y fecha.
3. **Dado:** datos obligatorios faltantes. **Cuando:** se intenta guardar. **Entonces:** se indica cuáles faltan.
4. **Dado:** un cliente sin domicilio cargado. **Cuando:** creo la orden. **Entonces:** puedo agregar el domicilio sin salir de la pantalla.
5. **Dado:** el origen del pedido. **Cuando:** creo la orden. **Entonces:** puedo indicar si llegó por WhatsApp, mail o teléfono.

## Notas técnicas

- `source = manual`. Las órdenes generadas por mantenimiento (E07-04) usan `source = maintenance`.
- Domicilio (E03-02): si el cliente tiene un solo domicilio activo, se elige solo. Si tiene varios, administración elige, sin valor por defecto para evitar errores.

## Preguntas abiertas

- ¿Hace falta registrar quién hizo el pedido y por qué canal, o alcanza con la descripción? En Persat las órdenes registran el solicitante y su cargo, el sector u oficina y el piso o ala, sobre todo en sanatorios y organismos públicos.
