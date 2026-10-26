---
id: E02-04
title: "Gestionar reparaciones"
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

# E02-04 Gestionar reparaciones

## Historia

**Como** administración, **quiero** mantener el listado de reparaciones predefinidas de cada falla, por tipo de equipo o generales, **para** que el técnico elija la reparación realizada de una lista.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea una reparación con un nombre, una falla y un tipo de equipo. **Entonces:** queda activa y aparece en el listado de reparaciones activas de ese tipo y de esa falla.
2. **Dado:** administración. **Cuando:** crea una reparación sin tipo de equipo. **Entonces:** es genérica y aparece en el listado de reparaciones activas de todos los tipos.
3. **Dado:** una reparación. **Cuando:** administración la renombra. **Entonces:** el nombre nuevo se ve en todo lugar que la referencia, porque las referencias son por id. Si cambia el significado y no solo el término, se crea una reparación nueva y se desactiva la vieja.
4. **Dado:** una reparación. **Cuando:** administración la desactiva. **Entonces:** deja de aparecer en los listados de activas, se sigue pudiendo consultar por id con su nombre y se puede reactivar.
5. **Dado:** un tipo de equipo desactivado. **Cuando:** se listan sus reparaciones activas. **Entonces:** no se ofrece ninguna de sus reparaciones específicas, aunque cada una conserve su propio estado. Las genéricas no se ven afectadas.
6. **Dado:** un nombre que ya existe, activo o inactivo, sin distinguir mayúsculas ni espacios al principio, al final o repetidos. **Cuando:** se intenta crear o renombrar una reparación con ese nombre en el mismo tipo de equipo, o entre una genérica y una específica de cualquier tipo. **Entonces:** se rechaza con 409 y un mensaje claro. El mismo nombre en dos tipos distintos se acepta. Los acentos sí distinguen.
7. **Dado:** un nombre vacío o de solo espacios. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
8. **Dado:** un tipo de equipo inexistente. **Cuando:** se intenta crear una reparación para él. **Entonces:** se rechaza con 404.
9. **Dado:** una base recién migrada. **Cuando:** se consulta el catálogo. **Entonces:** están las reparaciones de la lista inicial del cliente, cada una con su falla y su tipo de equipo (o genérica), activas y editables. Las que valen para varios tipos están una vez por tipo.
10. **Dado:** un técnico o dirección. **Cuando:** intenta listar, crear, editar, desactivar o reactivar reparaciones. **Entonces:** recibe acceso denegado (403).
11. **Dado:** una falla. **Cuando:** se listan las reparaciones activas de esa falla (y, si se indica, de un tipo de equipo). **Entonces:** solo aparecen las de esa falla. Si la falla está desactivada, no se ofrece ninguna.
12. **Dado:** una falla inexistente. **Cuando:** se intenta crear una reparación para ella o filtrar por ella. **Entonces:** se rechaza con 404.
13. **Dado:** una falla de un tipo de equipo. **Cuando:** se intenta crear para ella una reparación genérica o de otro tipo. **Entonces:** se rechaza con 422 y un mensaje claro: la falla tiene que aplicar al tipo de la reparación.

## Fuera de alcance

- Uso de las reparaciones al cerrar una orden, incluida la opción "Otro" con observación obligatoria: es de E05-04. "Otro" no es un valor del catálogo, se guarda como texto en el cierre (`repair_other_text`).
- Lectura del catálogo por el técnico: llega con E05-04, que ofrece solo los valores activos y muestra los inactivos que ya estén en uso.
- Cambiar el tipo de equipo o la falla de una reparación, o asociarla a varios tipos (pero no a todos). Se crea una nueva y se desactiva la vieja; las que valen para varios tipos se cargan una vez por tipo.
- Promover un texto de "Otro" a la lista (E02-07) e importación y exportación CSV (E02-08).
- Borrar reparaciones: solo se desactivan. El borrado lógico con `deleted_at` es de E12-02. Registro en la auditoría: E12-01.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Las reparaciones funcionan igual que las fallas (E02-03):** cada una es de un tipo de equipo o genérica. Resuelve la contradicción entre la historia original y el glosario (una lista sin tipo) y el modelo de datos (`repair.equipment_type_id`): si todas se cargan como genéricas, funciona como una lista única; si el cliente las quiere separar por tipo, ya se puede.
- **Mismas reglas que E02-03** para duplicados (también entre genéricas y específicas), permisos, renombrar por id y desactivar en lugar de borrar.
- **Cada reparación pertenece a una falla**, como en la planilla del cliente. Al cerrar, el técnico elige la falla y ve solo sus reparaciones. La falla tiene que aplicar al tipo de la reparación: una falla genérica sirve para cualquier reparación; una falla de un tipo, solo para reparaciones de ese tipo.
- **Lista inicial del cliente**, cargada por migración junto con las 3 fallas (todas genéricas). La clasificación por tipo de equipo la propuso MendoData y falta que el cliente la confirme; si cambia, se corrige desde la pantalla. Como casi todos los equipos actuales son aires acondicionados, la lista de aires es la prioritaria.
- **"Otros" no se carga como reparación.** La planilla lo lista en cada falla, pero "Otro" es la opción fija del cierre con observación obligatoria (E05-04).
- La regla de duplicados no cambia: un nombre es único dentro de su tipo de equipo (o entre genéricas), sin importar la falla.
- Los criterios originales 1 y 2 ("el técnico la ve al cerrar", "incluye Otro") pasan a E05-04. El original 3 ("una reparación desactivada se conserva en las órdenes") se cumple porque no hay borrado y las referencias son por id.
- Tamaño de S a M: mismo alcance que E02-03.

## Notas técnicas

- Tabla `repair` igual que `failure`, más `failure_id` obligatorio: `equipment_type_id` opcional (vacío = genérica), `name`, `is_active` e índice único sobre `(coalesce(equipment_type_id, <uuid cero>), lower(name))`. El cruce entre genéricas y específicas se chequea en el servicio. Actualizar `data-model.dbml`.
- Endpoints bajo `/admin/repairs` con el mismo contrato que `/admin/failures`, más `failure_id` al crear (obligatorio) y como filtro del listado.
- La lógica de fallas y reparaciones es la misma: extraer lo común (repositorio, servicio y, en web-admin, la pantalla) en vez de copiarlo.
- web-admin: pantalla "Reparaciones", igual que "Fallas" más un selector de falla. Desactivar o reactivar un tipo de equipo también tiene que refrescar las reparaciones.
- Si el PR pasa de unas 400 líneas, se divide en backend y web-admin.

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): endpoints `/admin/repairs` y `/admin/repairs/{id}`, con el mismo contrato que `/admin/failures`, todos con `require_role(admin)`. 409 con `repair_name_already_exists`; inexistente, 404 con `repair_not_found`.
  - Lo común con fallas se extrajo en vez de copiarse: modelo abstracto `EquipmentScopedCatalog` (columnas e índice único `uq_<tabla>_scope_name`), repositorio genérico `EquipmentScopedRepository` y funciones de servicio parametrizadas por catálogo. `Failure` y `Repair` solo declaran su tabla. Los tests de fallas pasan sin modificarse.
  - Los esquemas de la API tienen una clase por catálogo (`Failure*` y `Repair*`) sobre una base común, para que el cliente generado los nombre por separado.
  - Migración `11cec86d9eaa`: crea la tabla; el `downgrade` la borra.
- Backend (PR 2): cada reparación pertenece a una falla.
  - `repair.failure_id` obligatorio (migración `154f870b70dc`). No se edita después de crear, como el tipo de equipo.
  - Al crear: 404 `failure_not_found` si la falla no existe; 422 `repair_failure_mismatch` si la falla es de un tipo y la reparación es genérica o de otro tipo.
  - Listado con filtro opcional `failure_id`; una falla desactivada no ofrece reparaciones (con `include_inactive` sí).
  - Migración de datos `7a8a9559f9b4`: las 3 fallas genéricas y 36 reparaciones (48 filas, porque las de varios tipos van una vez por cada uno), sin "Otros". Busca los tipos de equipo por nombre y aborta si falta alguno. El `downgrade` borra solo lo que cargó.
- web-admin (PR 3): pantalla "Reparaciones" en `features/repairs/`, visible solo para administración.
  - Fallas y reparaciones comparten el componente `EquipmentScopedCatalogView` de `features/catalogs/` (selector de tipo de equipo, genéricas, alta, lista, desactivadas); cada pantalla le pasa sus textos y datos. Los tests de "Fallas" pasan sin cambios.
  - Selector de falla con "Todas" y solo las fallas que aplican al tipo elegido, para que no se pueda elegir una incompatible. Para dar de alta hay que elegir una falla. Con "Todas", cada reparación muestra el nombre de su falla.
  - Claves de caché en `catalogs/queryKeys.ts`: cambiar un tipo de equipo refresca fallas y reparaciones; cambiar una falla refresca las reparaciones.
  - Probada en el navegador contra el backend real con la lista del cliente.
