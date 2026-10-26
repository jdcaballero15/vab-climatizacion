---
id: E02-09
title: "Gestionar escuadrillas y técnicos"
epic: E02
phase: 1
priority: must
status: ready
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E01-03, E01-04]
blocked_by: []
assumes: []
---

# E02-09 Gestionar escuadrillas y técnicos

## Historia

**Como** administración, **quiero** cargar las escuadrillas con el usuario de su celular y la lista de técnicos, **para** asignar las órdenes a una escuadrilla y que al cerrar se pueda tildar quiénes fueron.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea una escuadrilla con un nombre ("Escuadrilla 1"). **Entonces:** queda activa y disponible para asignar órdenes.
2. **Dado:** una escuadrilla. **Cuando:** administración le asocia un usuario. **Entonces:** solo se ofrecen usuarios activos con rol técnico que no estén asociados a otra escuadrilla. Otro usuario se rechaza con 422.
3. **Dado:** un nombre de escuadrilla que ya existe (sin distinguir mayúsculas ni espacios de más, también contra las inactivas). **Cuando:** se intenta crear o renombrar. **Entonces:** se rechaza con 409.
4. **Dado:** una escuadrilla. **Cuando:** administración la desactiva. **Entonces:** deja de ofrecerse para asignar, pero las órdenes anteriores la siguen mostrando. (Que no se pueda desactivar con órdenes abiertas lo agrega E04-03, cuando las asignaciones tienen escuadrilla.)
5. **Dado:** administración. **Cuando:** carga un técnico con su nombre. **Entonces:** queda activo y aparece en la lista para tildar al cerrar (E05-04). Los técnicos no tienen usuario ni contraseña.
6. **Dado:** un técnico. **Cuando:** administración lo desactiva. **Entonces:** deja de aparecer para tildar, pero los cierres donde figura lo conservan.
7. **Dado:** las dos listas. **Cuando:** se consultan. **Entonces:** muestran primero los activos, por nombre, y se puede ver también los inactivos.
8. **Dado:** un técnico (usuario de escuadrilla) o dirección. **Cuando:** llama a la API de escuadrillas o técnicos. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Crear el usuario del celular: se hace en Usuarios (E01-03), con rol técnico. Acá solo se asocia.
- Tildar quiénes fueron al cerrar: E05-04.
- Asignar órdenes a una escuadrilla: E04-03.
- La camioneta de cada escuadrilla para el stock: E08-01.
- No hay borrado: escuadrillas y técnicos se desactivan.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26 (D-013):

- Las escuadrillas son una **lista fija con nombre**; lo que cambia son las personas que la forman.
- **Un usuario por celular**: cada escuadrilla tiene su usuario; quienes salen ese día usan ese celular.
- Los técnicos son personas sin usuario. Quiénes fueron se registra **al cerrar cada orden**.

## Notas técnicas

- Tablas `crew` (`name`, `app_user_id` único y opcional, `is_active`) y `field_technician` (`full_name`, `is_active`) según `data-model.dbml`. Índice único por `lower(name)` en `crew`, como en los catálogos de E02.
- Endpoints `/admin/crews` y `/admin/field-technicians` (listar con `include_inactive`, crear, editar) con `require_role(admin)`. Errores: `crew_not_found`, `crew_name_already_exists`, `crew_user_not_available`, `field_technician_not_found`.
- Web-admin: sección "Escuadrillas y técnicos" (como en Configuración del prototipo). Reutilizar los componentes de `features/catalogs/` donde se pueda.

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): `/admin/crews` y `/admin/field-technicians` (listar con `include_inactive`, crear, editar; escuadrillas también consultar) con `require_role(admin)`. Sin borrado. Migración `d3a9b6e2f417`: tablas `crew` (índice único por `lower(name)`, `app_user_id` único) y `field_technician` (índice único por `lower(full_name)`).
- Nombres recortados y sin espacios de más (`CatalogName`). Decidido en el plan: los técnicos con nombre repetido también se rechazan (409 `field_technician_name_already_exists`), para no tener dos iguales para tildar.
- Usuario del celular: al crear o editar, `app_user_id` tiene que ser un usuario activo con rol técnico que no esté en otra escuadrilla (si no, 422 `crew_user_not_available`). En la edición, `null` lo desasocia y no mandarlo lo deja como está. La respuesta trae el usuario (id, nombre, email y si está activo).
- Si después desactivan o cambian de rol al usuario desde Usuarios, la escuadrilla conserva el vínculo y la respuesta lo muestra inactivo.
- Listados: primero los activos, después por nombre.

