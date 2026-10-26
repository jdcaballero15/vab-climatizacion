---
id: E02-04
title: "Gestionar reparaciones"
epic: E02
phase: 1
priority: must
status: ready
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E02-02]
blocked_by: []
assumes: [D-003]
---

# E02-04 Gestionar reparaciones

## Historia

**Como** administración, **quiero** mantener el listado de reparaciones predefinidas, por tipo de equipo o generales, **para** que el técnico elija la reparación realizada de una lista.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea una reparación con un nombre y un tipo de equipo. **Entonces:** queda activa y aparece en el listado de reparaciones activas de ese tipo.
2. **Dado:** administración. **Cuando:** crea una reparación sin tipo de equipo. **Entonces:** es genérica y aparece en el listado de reparaciones activas de todos los tipos.
3. **Dado:** una reparación. **Cuando:** administración la renombra. **Entonces:** el nombre nuevo se ve en todo lugar que la referencia, porque las referencias son por id. Si cambia el significado y no solo el término, se crea una reparación nueva y se desactiva la vieja.
4. **Dado:** una reparación. **Cuando:** administración la desactiva. **Entonces:** deja de aparecer en los listados de activas, se sigue pudiendo consultar por id con su nombre y se puede reactivar.
5. **Dado:** un tipo de equipo desactivado. **Cuando:** se listan sus reparaciones activas. **Entonces:** no se ofrece ninguna de sus reparaciones específicas, aunque cada una conserve su propio estado. Las genéricas no se ven afectadas.
6. **Dado:** un nombre que ya existe, activo o inactivo, sin distinguir mayúsculas ni espacios al principio, al final o repetidos. **Cuando:** se intenta crear o renombrar una reparación con ese nombre en el mismo tipo de equipo, o entre una genérica y una específica de cualquier tipo. **Entonces:** se rechaza con 409 y un mensaje claro. El mismo nombre en dos tipos distintos se acepta. Los acentos sí distinguen.
7. **Dado:** un nombre vacío o de solo espacios. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
8. **Dado:** un tipo de equipo inexistente. **Cuando:** se intenta crear una reparación para él. **Entonces:** se rechaza con 404.
9. **Dado:** una base recién migrada. **Cuando:** se consulta el catálogo. **Entonces:** está vacío. Administración carga las reparaciones.
10. **Dado:** un técnico o dirección. **Cuando:** intenta listar, crear, editar, desactivar o reactivar reparaciones. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Uso de las reparaciones al cerrar una orden, incluida la opción "Otro" con observación obligatoria: es de E05-04. "Otro" no es un valor del catálogo, se guarda como texto en el cierre (`repair_other_text`).
- Lectura del catálogo por el técnico: llega con E05-04, que ofrece solo los valores activos y muestra los inactivos que ya estén en uso.
- Cambiar el tipo de equipo de una reparación, o asociarla a varios tipos (pero no a todos). Igual que en E02-03.
- Promover un texto de "Otro" a la lista (E02-07) e importación y exportación CSV (E02-08).
- Borrar reparaciones: solo se desactivan. El borrado lógico con `deleted_at` es de E12-02. Registro en la auditoría: E12-01.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Las reparaciones funcionan igual que las fallas (E02-03):** cada una es de un tipo de equipo o genérica. Resuelve la contradicción entre la historia original y el glosario (una lista sin tipo) y el modelo de datos (`repair.equipment_type_id`): si todas se cargan como genéricas, funciona como una lista única; si el cliente las quiere separar por tipo, ya se puede.
- **Mismas reglas que E02-03** para duplicados (también entre genéricas y específicas), permisos, renombrar por id y desactivar en lugar de borrar.
- **Sin lista inicial.** Si el cliente la pasa, se carga por migración.
- Los criterios originales 1 y 2 ("el técnico la ve al cerrar", "incluye Otro") pasan a E05-04. El original 3 ("una reparación desactivada se conserva en las órdenes") se cumple porque no hay borrado y las referencias son por id.
- Tamaño de S a M: mismo alcance que E02-03.

## Notas técnicas

- Tabla `repair` igual que `failure`: `equipment_type_id` opcional (vacío = genérica), `name`, `is_active` e índice único sobre `(coalesce(equipment_type_id, <uuid cero>), lower(name))`. El cruce entre genéricas y específicas se chequea en el servicio. Actualizar `data-model.dbml`.
- Endpoints bajo `/admin/repairs` con el mismo contrato que `/admin/failures`.
- La lógica de fallas y reparaciones es la misma: extraer lo común (repositorio, servicio y, en web-admin, la pantalla) en vez de copiarlo.
- web-admin: pantalla "Reparaciones", igual que "Fallas". Desactivar o reactivar un tipo de equipo también tiene que refrescar las reparaciones.
- Si el PR pasa de unas 400 líneas, se divide en backend y web-admin.

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): endpoints `/admin/repairs` y `/admin/repairs/{id}`, con el mismo contrato que `/admin/failures`, todos con `require_role(admin)`. 409 con `repair_name_already_exists`; inexistente, 404 con `repair_not_found`.
  - Lo común con fallas se extrajo en vez de copiarse: modelo abstracto `EquipmentScopedCatalog` (columnas e índice único `uq_<tabla>_scope_name`), repositorio genérico `EquipmentScopedRepository` y funciones de servicio parametrizadas por catálogo. `Failure` y `Repair` solo declaran su tabla. Los tests de fallas pasan sin modificarse.
  - Los esquemas de la API tienen una clase por catálogo (`Failure*` y `Repair*`) sobre una base común, para que el cliente generado los nombre por separado.
  - Migración `11cec86d9eaa`: crea la tabla sin datos; el `downgrade` la borra.
- web-admin (PR 2): pendiente.
