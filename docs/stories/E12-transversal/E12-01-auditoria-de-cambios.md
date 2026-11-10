---
id: E12-01
title: "Auditoría de cambios"
epic: E12
phase: 1
priority: must
status: done
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E12-01 Auditoría de cambios

## Historia

**Como** dirección, **quiero** que los cambios sobre órdenes, catálogos, precios, stock y usuarios queden registrados con quién, cuándo y qué cambió, **para** saber qué pasó ante una duda o un error.

## Criterios de aceptación

1. **Dado:** una entidad auditada. **Cuando:** se crea, modifica o se da de baja. **Entonces:** se agrega un registro en `audit_log` con usuario, fecha, entidad, acción y diferencias.
2. **Dado:** dirección o administración. **Cuando:** consulta la auditoría. **Entonces:** puede filtrar por entidad, usuario y fecha.
3. **Dado:** el registro de auditoría. **Cuando:** se consulta. **Entonces:** no se puede editar ni borrar desde la aplicación.
4. **Dado:** los datos personales (DNI). **Cuando:** aparecen en una diferencia. **Entonces:** se enmascaran.

## Decisiones (2026-11-10)

- La tabla se llama `audit_event` (la historia decía `audit_log`).

## Hecho

- Se registra solo en `audit_event` (la tabla de E12-02): un listener del flush de SQLAlchemy (`app/db/audit_listener.py`) anota altas, cambios, bajas, restauraciones y unificaciones de órdenes, cobro, catálogos, precios, clientes, equipos, escuadrillas, mantenimiento, stock y usuarios, con el usuario que hizo el pedido (lo pone `require_role`) y las diferencias en JSON. Lo que corre sin usuario (importaciones, procesos programados) tiene su propio registro.
- El CUIT o DNI (`tax_id`) se guarda como `***`; las contraseñas no se guardan (criterio 4). `actor_id` sin clave foránea.
- `GET /admin/audit` (administración y dirección), paginado, filtra por entidad, usuario, registro y fechas. No hay rutas para editar ni borrar (criterio 3).
- web-admin: "Auditoría" en Equipo.
