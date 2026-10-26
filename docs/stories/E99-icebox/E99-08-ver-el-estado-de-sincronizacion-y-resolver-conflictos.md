---
id: E99-08
title: "Ver el estado de sincronización y resolver conflictos"
epic: E99
phase: 2
priority: could
status: icebox
roles: [technician, admin]
size: M
areas: [backend, pwa, web-admin]
depends_on: []
blocked_by: []
assumes: []
---

# E99-08 Ver el estado de sincronización y resolver conflictos

## Historia

**Como** técnico, **quiero** ver qué cierres están pendientes, sincronizados o con error, **para** saber que mi trabajo llegó a la oficina.

## Criterios de aceptación

1. **Dado:** una lista de órdenes. **Cuando:** miro cada una. **Entonces:** muestra si está pendiente de sincronizar, sincronizada o con error.
2. **Dado:** un cierre con error. **Cuando:** el técnico lo abre. **Entonces:** ve el motivo en lenguaje simple y puede reintentar.
3. **Dado:** una orden reasignada o cancelada mientras el técnico estaba sin señal. **Cuando:** llega su cierre. **Entonces:** el cierre queda "en revisión" y no se pierde.
4. **Dado:** administración. **Cuando:** abre los cierres en revisión. **Entonces:** puede aceptar el cierre, reasignarlo o descartarlo con motivo.

## Notas técnicas

- Reglas de conflicto del ADR 0003: el cierre del técnico se agrega, lo de la oficina gana el servidor.

## Icebox

- Venía de la épica E05. Pasa al icebox por `D-001` (2026-10-26): según el relevamiento las cuadrillas siempre tienen señal y la app del técnico funciona solo con conexión (ADR 0009). Lo mínimo para no perder un cierre si se corta la señal está en E05-13. Se retoma si en la práctica aparecen lugares sin señal.
