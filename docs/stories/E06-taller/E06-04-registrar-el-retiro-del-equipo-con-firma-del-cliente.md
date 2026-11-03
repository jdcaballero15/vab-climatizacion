---
id: E06-04
title: "Registrar el retiro del equipo con firma del cliente"
epic: E06
phase: 1
priority: must
status: done
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E06-03, E05-07]
blocked_by: []
assumes: []
---

# E06-04 Registrar el retiro del equipo con firma del cliente

## Historia

**Como** técnico, **quiero** registrar el retiro de un equipo con la firma del cliente, **para** tener constancia de que se llevó el equipo y en qué estado.

## Criterios de aceptación

1. **Dado:** una etapa de retiro asignada a mí. **Cuando:** la completo con firma, nombre y DNI del cliente. **Entonces:** la etapa queda `done` y el equipo figura en el galpón.
2. **Dado:** una etapa de retiro sin firma. **Cuando:** intento completarla. **Entonces:** se rechaza.
3. **Dado:** el retiro completado. **Cuando:** se consulta. **Entonces:** se puede generar el comprobante PDF (E09-01).
4. **Dado:** el técnico. **Cuando:** ve la etapa. **Entonces:** no ve precios ni historial.

## Refinamiento y avance

Acordado con Gonza el 2026-11-03 (escuadrillas en todo, firma y nombre sin DNI, nace desde la visita y desde la oficina, PDF más adelante, etapas en fila: opción A del ADR 0007) y hecho el mismo día:

- "Retiro hecho" exige firma y nombre (sin DNI, decisión del 2026-11-03), no pide falla, reparación ni estado del equipo. La firma queda con propósito `pickup`. La orden vuelve a Pendiente con la etapa Galpón. El técnico no ve precios ni historial (mismos esquemas). El PDF (criterio 3) queda para E09-01.
