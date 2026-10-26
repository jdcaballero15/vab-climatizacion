---
id: E02-02
title: "Gestionar tipos de equipo"
epic: E02
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E01-04]
blocked_by: []
assumes: [D-003]
---

# E02-02 Gestionar tipos de equipo

## Historia

**Como** administración, **quiero** editar los tipos de equipo (por ejemplo split, cámara frigorífica, heladera comercial), **para** clasificar equipos, fallas y checklists por tipo.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un tipo de equipo con un nombre. **Entonces:** queda activo y aparece en el listado de tipos activos.
2. **Dado:** un tipo de equipo. **Cuando:** administración lo renombra. **Entonces:** el nombre nuevo se ve en todo lugar que lo referencia, porque las referencias son por id. Si cambia el significado y no solo el término, se crea un tipo nuevo y se desactiva el viejo.
3. **Dado:** un tipo de equipo. **Cuando:** administración lo desactiva. **Entonces:** deja de aparecer en el listado de activos, se sigue pudiendo consultar por id con su nombre y se puede reactivar.
4. **Dado:** un nombre que ya existe, activo o inactivo, sin distinguir mayúsculas ni espacios al principio, al final o repetidos. **Cuando:** se intenta crear o renombrar un tipo de equipo con ese nombre. **Entonces:** se rechaza con 409 y un mensaje claro. Los acentos sí distinguen.
5. **Dado:** un nombre vacío o de solo espacios. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
6. **Dado:** una base recién migrada. **Cuando:** se consulta el catálogo. **Entonces:** está vacío. Administración carga los tipos.
7. **Dado:** un técnico o dirección. **Cuando:** intenta listar, crear, editar, desactivar o reactivar tipos de equipo. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Uso de los tipos en equipos (E03-03), fallas (E02-03), reparaciones (E02-04) y plantillas de checklist (E07-01). Cada una de esas historias ofrece solo los tipos activos y muestra los inactivos que ya estén en uso.
- Borrar tipos: solo se desactivan, también los que tengan equipos o checklists asociados. El borrado lógico con `deleted_at` y la restauración son de E12-02.
- Importación y exportación CSV (E02-08).
- Registro en la auditoría: llega con E12-01.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Mismas reglas que E02-01.** Renombrar se ve en todos lados (referencia por id), duplicados sin distinguir mayúsculas ni espacios y también contra inactivos, los acentos distinguen, solo administración edita.
- **No hay borrado, solo desactivar.** Reemplaza al criterio original "si tiene equipos o checklists asociados no se puede borrar": como en E02-01, en catálogos no hay baja, así que ese caso no se da.
- **Sin lista inicial.** La lista de tipos la tiene que pasar el cliente. Mientras tanto la migración no carga ningún valor y administración los da de alta desde la pantalla.

## Notas técnicas

- Tabla `equipment_type` con `TimestampedBase`, `is_active` e índice único sobre `lower(name)`, como `work_type`. El nombre se guarda recortado y con los espacios colapsados. Actualizar `data-model.dbml`, que hoy no tiene `is_active`.
- Endpoints bajo `/admin/equipment-types` (listar con `include_inactive`, crear, ver, editar) con `require_role(admin)`. Desactivar y reactivar es `PATCH` con `is_active`. Duplicado: 409 con `equipment_type_name_already_exists`; no encontrado: 404 con `equipment_type_not_found`.
- Reusar el servicio y los repositorios de catálogos de E02-01 (`services/catalog.py`, `db/repositories/catalog.py`).
- web-admin: pantalla "Tipos de equipo" con alta, edición del nombre, desactivar y reactivar, y ver los desactivados. Reusar `CatalogItem` y `NewNameForm` de `features/work-types/`.
- Si el PR pasa de unas 400 líneas, se divide en backend y web-admin, como en E02-01.

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend: endpoints `/admin/equipment-types` y `/admin/equipment-types/{id}` (listar con `include_inactive`, crear, ver, editar), todos con `require_role(admin)`. Lógica en `services/catalog.py`, repositorio `EquipmentTypeRepository` en `db/repositories/catalog.py`.
  - Desactivar y reactivar es `PATCH` con `is_active`, no `DELETE`.
  - Duplicados: chequeo en el servicio e índice único `uq_equipment_type_name` sobre `lower(name)` como respaldo. 409 con `equipment_type_name_already_exists`; inexistente, 404 con `equipment_type_not_found`.
  - Migración `891a93da0872`: crea la tabla sin tipos iniciales; el `downgrade` la borra.
- web-admin: pantalla "Tipos de equipo" en `features/equipment-types/`, visible solo para administración, con alta, renombrar, desactivar y reactivar, ver los desactivados y un aviso cuando el catálogo está vacío. Reusa `CatalogItem`, `NewNameForm` y `NameTakenError` de `features/work-types/`.
  - Se regeneró `openapi.json` y `src/api/schema.d.ts` desde el backend.
- `EquipmentTypeRepository` repite el patrón de `WorkTypeRepository`. Con fallas y reparaciones (E02-03, E02-04) conviene extraer una base común para catálogos, y decidir si los componentes compartidos se mueven fuera de `features/work-types/`.
