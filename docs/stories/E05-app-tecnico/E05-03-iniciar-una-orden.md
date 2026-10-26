---
id: E05-03
title: "Iniciar una orden"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: S
areas: [backend, pwa]
depends_on: [E05-02, E04-01]
blocked_by: []
assumes: []
---

# E05-03 Iniciar una orden

## Historia

**Como** técnico, **quiero** marcar que empiezo una orden, **para** que administración sepa que estoy trabajando en ella.

## Criterios de aceptación

1. **Dado:** una orden `Asignada` a mí. **Cuando:** toco "Iniciar". **Entonces:** pasa a `En curso` y queda un evento con usuario y fecha.
2. **Dado:** una orden de otro técnico. **Cuando:** intento iniciarla. **Entonces:** se rechaza.
3. **Dado:** una orden que ya está `En curso`. **Cuando:** toco "Iniciar" de nuevo. **Entonces:** no cambia nada ni se duplica el evento.

## Decisiones

- **Se mantiene el botón "Iniciar"** (negocio, 2026-10-26), aunque el prototipo del cliente cierra directo sin iniciar: así administración ve qué orden se está trabajando.

## Fuera de alcance

- Registro de hora de llegada y salida: confirmado que NO se registra. El evento de inicio es solo el cambio de estado.
