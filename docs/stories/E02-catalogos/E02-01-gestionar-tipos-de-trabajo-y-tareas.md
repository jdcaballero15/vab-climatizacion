---
id: E02-01
title: "Gestionar tipos de trabajo y tareas"
epic: E02
phase: 1
priority: must
status: ready
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E01-04]
blocked_by: []
assumes: [D-003]
---

# E02-01 Gestionar tipos de trabajo y tareas

## Historia

**Como** administración, **quiero** editar los tipos de trabajo (instalación, reparación, service, devolución, retiro, relevamiento) y sus subtareas, **para** estandarizar los términos sin depender de desarrollo.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un tipo de trabajo con un nombre. **Entonces:** queda activo y aparece en el listado de tipos activos.
2. **Dado:** un tipo de trabajo. **Cuando:** administración lo renombra. **Entonces:** el nombre nuevo se ve en todo lugar que lo referencia, porque las referencias son por id. Si cambia el significado y no solo el término, se crea un tipo nuevo y se desactiva el viejo.
3. **Dado:** un tipo de trabajo. **Cuando:** administración le agrega, renombra o desactiva subtareas. **Entonces:** el listado de subtareas activas de ese tipo refleja el cambio.
4. **Dado:** un tipo de trabajo o una subtarea. **Cuando:** administración lo desactiva. **Entonces:** deja de aparecer en los listados de activos, se sigue pudiendo consultar por id con su nombre y se puede reactivar.
5. **Dado:** un tipo de trabajo desactivado. **Cuando:** se listan sus subtareas activas. **Entonces:** no se ofrece ninguna, aunque cada una conserve su propio estado.
6. **Dado:** un nombre que ya existe, activo o inactivo, sin distinguir mayúsculas ni espacios al principio, al final o repetidos. **Cuando:** se intenta crear o renombrar un tipo de trabajo con ese nombre. **Entonces:** se rechaza con 409 y un mensaje claro. Los acentos sí distinguen ("Instalacion" e "Instalación" son distintos).
7. **Dado:** el caso anterior aplicado a subtareas. **Cuando:** se repite el nombre dentro del mismo tipo de trabajo. **Entonces:** se rechaza con 409. El mismo nombre en tipos distintos se acepta.
8. **Dado:** un nombre vacío o de solo espacios. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
9. **Dado:** una base recién migrada. **Cuando:** se consulta el catálogo. **Entonces:** están los seis tipos iniciales (Instalación, Reparación, Service, Devolución, Retiro, Relevamiento), activos y editables.
10. **Dado:** un técnico o dirección. **Cuando:** intenta crear, editar, desactivar o reactivar tipos o subtareas. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Uso de los tipos y subtareas en las órdenes: al crearlas (E04-02) y al cerrarlas (E05-04). Cada una de esas historias ofrece solo los valores activos y muestra los inactivos que ya estén en uso.
- Lectura del catálogo por el técnico para cerrar órdenes: llega con E05-04.
- Importación y exportación CSV (E02-08) y promover un "Otro" a la lista (E02-07).
- Mover una subtarea a otro tipo de trabajo. Se crea en el tipo correcto y se desactiva la vieja.
- Borrar tipos o subtareas: solo se desactivan. El borrado lógico con `deleted_at` y la restauración son de E12-02.
- Registro en la auditoría: llega con E12-01.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Renombrar se ve en todas las órdenes, también en las pasadas.** No se guarda una copia del nombre en la orden.
- **Duplicados:** se comparan sin distinguir mayúsculas y sin los espacios al principio, al final ni repetidos. También se compara contra los inactivos, para reactivar en lugar de duplicar. Los acentos sí cuentan.
- **Permisos:** solo administración edita catálogos, como dice la matriz de `roles-permisos.md`. Dirección no edita.

## Notas técnicas

- Tablas `work_type` y `task` con `TimestampedBase`. Unicidad en la base con un índice único sobre el nombre normalizado (`lower` y espacios colapsados), global en `work_type` y por `work_type_id` en `task`. El nombre se guarda recortado y con los espacios colapsados.
- Los seis tipos iniciales se cargan en una migración Alembic de datos, reversible, porque también tienen que existir en producción. No van en `make seed`, que es para datos ficticios. El chequeo de "base vacía" del generador (E11-09) no debe contar estos valores.
- Ninguna subtarea inicial: no hay una lista relevada. Administración las carga.
- Endpoints bajo `/admin/work-types` y `/admin/work-types/{id}/tasks` con `require_role(admin)`. Los listados filtran por activos y permiten pedir también los inactivos para la pantalla de administración.
- web-admin: pantalla de tipos de trabajo con sus subtareas, alta, edición del nombre, desactivar y reactivar.
- Si el PR pasa de unas 400 líneas, se divide en backend y web-admin, como en E01-02.
