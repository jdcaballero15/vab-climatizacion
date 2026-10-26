---
id: E99-07
title: "Cola de cierres pendientes de sincronizar"
epic: E99
phase: 2
priority: could
status: icebox
roles: [technician]
size: L
areas: [pwa]
depends_on: []
blocked_by: []
assumes: []
---

# E99-07 Cola de cierres pendientes de sincronizar

## Historia

**Como** técnico, **quiero** que mis cierres, firmas y fotos queden en una cola y se envíen solos cuando vuelva la señal, **para** no perder trabajo hecho sin conexión.

## Criterios de aceptación

1. **Dado:** un cierre completado sin señal. **Cuando:** toco "Enviar". **Entonces:** queda guardado en la cola local con una clave de idempotencia.
2. **Dado:** la señal que vuelve. **Cuando:** la app lo detecta. **Entonces:** envía la cola en orden sin acción del técnico.
3. **Dado:** un envío reintentado por corte de red. **Cuando:** el servidor ya lo había recibido. **Entonces:** no se duplica el cierre.
4. **Dado:** una foto o firma. **Cuando:** se sube con mala señal. **Entonces:** se reintenta hasta lograrlo.
5. **Dado:** el técnico que cierra la app o apaga el celular. **Cuando:** lo vuelve a abrir. **Entonces:** la cola sigue intacta.

## Icebox

- Venía de la épica E05. Pasa al icebox por `D-001` (2026-10-26): según el relevamiento las cuadrillas siempre tienen señal y la app del técnico funciona solo con conexión (ADR 0009). Lo mínimo para no perder un cierre si se corta la señal está en E05-13. Se retoma si en la práctica aparecen lugares sin señal.
