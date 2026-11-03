---
id: E07-03
title: "Gestionar abonos: equipos incluidos y frecuencia"
epic: E07
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-03]
blocked_by: []
assumes: [D-002]
---

# E07-03 Gestionar abonos: equipos incluidos y frecuencia

## Historia

**Como** administración, **quiero** definir qué equipos de cada cliente tienen mantenimiento, cada cuántos meses se visitan y cuándo toca la próxima visita, **para** que el sistema genere solo el mantenimiento que corresponde.

## Lo acordado

Decisión de Gonza (2026-11-03), siguiendo el prototipo del cliente: **un plan por equipo**, no un abono con varios equipos. Cada plan tiene cada cuántos meses se visita (1, 2, 3, 4, 6 o 12), la próxima visita, la escuadrilla que suele ir (opcional, viene elegida al asignar), el tipo de trabajo (se propone "Service") e indicaciones para la escuadrilla.

## Criterios de aceptación

1. **Dado:** un equipo de un cliente. **Cuando:** administración le crea un plan con frecuencia y próxima visita. **Entonces:** esa visita entra en la próxima generación (E07-04).
2. **Dado:** un plan. **Cuando:** administración le pone fecha de fin (o lo termina desde la lista, con fin hoy). **Entonces:** desde esa fecha no se generan visitas y el plan queda como historial ("Ver también los terminados").
3. **Dado:** un equipo. **Cuando:** ya tiene un plan activo y se le crea otro, o se reabre uno terminado. **Entonces:** se rechaza (409 `equipment_already_in_plan`).
4. **Dado:** un plan. **Cuando:** se elige un equipo dado de baja, un tipo de trabajo o una escuadrilla desactivados. **Entonces:** se rechaza con el motivo.
5. **Dado:** el rol técnico. **Cuando:** intenta ver o editar planes. **Entonces:** recibe acceso denegado.

## Notas técnicas

- Tabla `maintenance_plan` (migración `451cd042f251`). Las fechas del plan viven en el plan; las de cada visita, en la orden (`maintenance_due_on`, ADR 0005).
- API: `GET/POST /admin/maintenance/plans`, `GET/PATCH /admin/maintenance/plans/{id}`. La lista trae la última orden generada que sigue abierta.
- Web-admin: pestaña "Mantenimiento" con la lista, alta, edición y "Terminar" con confirmación.
- La auditoría del cambio (criterio 4 original) queda para la auditoría general: hoy no hay una tabla de auditoría.
- La carga inicial de los abonados reales va aparte, con el archivo de Gonza.
