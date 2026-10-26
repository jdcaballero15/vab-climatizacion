---
id: E99-06
title: "Guardar mis órdenes en el celular para trabajar sin señal"
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

# E99-06 Guardar mis órdenes en el celular para trabajar sin señal

## Historia

**Como** técnico, **quiero** tener mis órdenes guardadas en el celular, **para** poder trabajar en cámaras, sótanos o zonas rurales sin señal.

## Criterios de aceptación

1. **Dado:** un técnico con conexión. **Cuando:** abre la app. **Entonces:** sus órdenes asignadas se guardan en el celular.
2. **Dado:** el celular sin señal. **Cuando:** abre la app. **Entonces:** ve y abre sus órdenes guardadas.
3. **Dado:** lo guardado en el celular. **Cuando:** se inspecciona. **Entonces:** no contiene precios, mano de obra ni historial.
4. **Dado:** un técnico que cierra sesión. **Cuando:** hay datos locales. **Entonces:** se borran tras confirmar que no hay cierres sin sincronizar.

## Notas técnicas

- IndexedDB. Ver ADR 0003 (reemplazado por ADR 0009).

## Icebox

- Venía de la épica E05. Pasa al icebox por `D-001` (2026-10-26): según el relevamiento las cuadrillas siempre tienen señal y la app del técnico funciona solo con conexión (ADR 0009). Lo mínimo para no perder un cierre si se corta la señal está en E05-13. Se retoma si en la práctica aparecen lugares sin señal.
