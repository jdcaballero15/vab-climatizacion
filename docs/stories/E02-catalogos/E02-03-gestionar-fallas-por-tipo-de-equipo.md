---
id: E02-03
title: "Gestionar fallas por tipo de equipo"
epic: E02
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E02-02]
blocked_by: []
assumes: [D-003]
---

# E02-03 Gestionar fallas por tipo de equipo

## Historia

**Como** administración, **quiero** mantener el listado de fallas predefinidas por tipo de equipo, **para** que el técnico elija la falla de una lista y se pueda medir qué se rompe más.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea una falla con un nombre y un tipo de equipo. **Entonces:** queda activa y aparece en el listado de fallas activas de ese tipo.
2. **Dado:** administración. **Cuando:** crea una falla sin tipo de equipo. **Entonces:** es genérica y aparece en el listado de fallas activas de todos los tipos.
3. **Dado:** una falla. **Cuando:** administración la renombra. **Entonces:** el nombre nuevo se ve en todo lugar que la referencia, porque las referencias son por id. Si cambia el significado y no solo el término, se crea una falla nueva y se desactiva la vieja.
4. **Dado:** una falla. **Cuando:** administración la desactiva. **Entonces:** deja de aparecer en los listados de activas, se sigue pudiendo consultar por id con su nombre y se puede reactivar.
5. **Dado:** un tipo de equipo desactivado. **Cuando:** se listan sus fallas activas. **Entonces:** no se ofrece ninguna de sus fallas específicas, aunque cada una conserve su propio estado. Las genéricas no se ven afectadas.
6. **Dado:** un nombre que ya existe, activo o inactivo, sin distinguir mayúsculas ni espacios al principio, al final o repetidos. **Cuando:** se intenta crear o renombrar una falla con ese nombre en el mismo tipo de equipo, o entre una genérica y una específica de cualquier tipo. **Entonces:** se rechaza con 409 y un mensaje claro. El mismo nombre en dos tipos distintos se acepta. Los acentos sí distinguen.
7. **Dado:** un nombre vacío o de solo espacios. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
8. **Dado:** un tipo de equipo inexistente. **Cuando:** se intenta crear una falla para él. **Entonces:** se rechaza con 404.
9. **Dado:** una base recién migrada. **Cuando:** se consulta el catálogo. **Entonces:** está vacío. Administración carga las fallas.
10. **Dado:** un técnico o dirección. **Cuando:** intenta listar, crear, editar, desactivar o reactivar fallas. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Uso de las fallas al cerrar una orden, incluida la opción "Otro" con observación obligatoria: es de E05-04. "Otro" no es un valor del catálogo, se guarda como texto en el cierre (`failure_other_text`).
- Lectura del catálogo por el técnico: llega con E05-04, que ofrece solo los valores activos y muestra los inactivos que ya estén en uso.
- Cambiar el tipo de equipo de una falla. Se crea en el tipo correcto y se desactiva la vieja, como con las subtareas de E02-01.
- Que una falla aplique a varios tipos (pero no a todos). Se carga como genérica o una vez por tipo.
- Promover un texto de "Otro" a la lista (E02-07) e importación y exportación CSV (E02-08).
- Borrar fallas: solo se desactivan. El borrado lógico con `deleted_at` es de E12-02. Registro en la auditoría: E12-01.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Mismas reglas que E02-01 y E02-02.** Renombrar se ve en todos lados (referencia por id), duplicados sin distinguir mayúsculas ni espacios y también contra inactivas, los acentos distinguen, solo administración edita, no hay borrado.
- **Una falla aplica a un tipo de equipo o a todos** (genérica), como dice el modelo de datos. No hay asociación a varios tipos.
- **Duplicados entre genéricas y específicas:** si existe la genérica "No enfría", no se puede crear "No enfría" para un tipo, y al revés. El técnico vería dos opciones iguales en la misma lista.
- **Sin lista inicial.** La lista de fallas más comunes por tipo la tiene que pasar el cliente. Mientras tanto administración las carga desde la pantalla; si llega antes de implementar, se carga por migración como los tipos de equipo.
- Los criterios originales 1 y 3 ("el técnico la ve al cerrar", "siempre incluye Otro") pasan a E05-04, que es donde el técnico usa la lista. El criterio original 4 ("una falla desactivada se conserva en las órdenes") se cumple porque no hay borrado y las referencias son por id.

## Notas técnicas

- Tabla `failure` con `TimestampedBase`, `equipment_type_id` opcional (vacío = genérica), `name` e `is_active`. El nombre se guarda recortado y con los espacios colapsados. Actualizar `data-model.dbml` (`is_active` hoy no es `not null`).
- Unicidad dentro del mismo alcance con un índice único sobre `(coalesce(equipment_type_id, <uuid cero>), lower(name))`, que también cubre genéricas entre sí. El cruce entre genéricas y específicas no se puede expresar con un índice: se chequea en el servicio.
- Endpoints bajo `/admin/failures` con `require_role(admin)`. El listado filtra por `equipment_type_id` (devuelve las de ese tipo más las genéricas) y permite pedir también las inactivas. Desactivar y reactivar es `PATCH` con `is_active`.
- Reusar el servicio, los repositorios y los componentes de catálogos de E02-01 y E02-02. Los componentes compartidos de web-admin (`CatalogItem`, `NewNameForm`, `NameTakenError`) se mueven antes a `web-admin/src/features/catalogs/`, en una PR de refactor aparte.
- web-admin: pantalla "Fallas" con selector de tipo de equipo (o "Genéricas"), alta, edición del nombre, desactivar y reactivar.
- Si el PR pasa de unas 400 líneas, se divide en backend y web-admin.

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): endpoints `/admin/failures` y `/admin/failures/{id}` (listar, crear, ver, editar), todos con `require_role(admin)`. Lógica en `services/catalog.py`, repositorio `FailureRepository` en `db/repositories/catalog.py`.
  - El listado sin `equipment_type_id` devuelve todas las fallas; con él, las de ese tipo más las genéricas (404 si el tipo no existe). Si el tipo está desactivado y no se piden inactivas, solo las genéricas.
  - Desactivar y reactivar es `PATCH` con `is_active`. El tipo de equipo de una falla no se edita.
  - Duplicados: el servicio busca choques (una genérica contra todas, una específica contra las de su tipo y las genéricas). Como respaldo, índice único `uq_failure_scope_name` sobre `(coalesce(equipment_type_id, uuid cero), lower(name))`, que hace chocar también a dos genéricas. 409 con `failure_name_already_exists`; inexistente, 404 con `failure_not_found`.
  - Riesgo aceptado: dos guardados simultáneos de una genérica y una específica con el mismo nombre pueden pasar ambos, porque ese cruce no está en el índice.
  - Migración `4094833fa904`: crea la tabla sin datos; el `downgrade` la borra.
- web-admin (PR 2): pantalla "Fallas" en `features/failures/`, visible solo para administración.
  - Selector de tipo de equipo con "Genéricas" (por defecto) y todos los tipos, también los desactivados marcados como tales, para poder administrar sus fallas.
  - En "Genéricas" se piden todas las fallas y se muestran las que no tienen tipo. Con un tipo elegido se muestran las suyas y las genéricas, marcadas "Genérica".
  - El alta crea la falla para el tipo elegido, o genérica. Renombrar, desactivar, reactivar y ver desactivadas, con `CatalogItem` y `NewNameForm` de `features/catalogs/`.
  - Se regeneró `openapi.json` y `src/api/schema.d.ts` desde el backend.
