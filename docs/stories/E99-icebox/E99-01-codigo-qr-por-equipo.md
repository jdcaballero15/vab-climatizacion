---
id: E99-01
title: "Código QR por equipo"
epic: E99
phase: 2
priority: could
status: icebox
roles: [technician, admin]
size: L
areas: [backend, pwa, web-admin]
depends_on: []
blocked_by: []
assumes: []
---

# E99-01 Código QR por equipo

## Historia

**Como** técnico, **quiero** escanear el código QR pegado en el equipo, **para** identificarlo sin equivocarme y sin buscarlo a mano.

## Criterios de aceptación

1. **Dado:** un equipo con QR. **Cuando:** el técnico lo escanea. **Entonces:** la app abre la orden o el equipo correspondiente.
2. **Dado:** administración. **Cuando:** imprime las etiquetas. **Entonces:** obtiene un PDF listo para imprimir con el QR de cada equipo.

## Notas técnicas

- El cliente contestó que lo evaluaría. No es un sí firme, por eso queda fuera de la Fase 1. Si vuelve, se apoya en el código interno del equipo (`D-002`).
