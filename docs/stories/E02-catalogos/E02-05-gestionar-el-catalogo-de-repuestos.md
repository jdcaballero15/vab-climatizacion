---
id: E02-05
title: "Gestionar el catálogo de repuestos"
epic: E02
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E01-04, E00-04]
blocked_by: []
assumes: [D-003]
---

# E02-05 Gestionar el catálogo de repuestos

## Historia

**Como** administración, **quiero** mantener el catálogo de repuestos con nombre y unidad, **para** que el técnico elija materiales de una lista y se sepa qué se usa.

En la interfaz se llaman **materiales**. En el código siguen siendo `part`.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** da de alta un material con nombre y unidad. **Entonces:** queda activo, con precio 0, y disponible para los cierres.
2. **Dado:** un material. **Cuando:** se guarda sin código. **Entonces:** es válido (hoy los materiales no tienen código).
3. **Dado:** un nombre muy parecido a uno existente. **Cuando:** se escribe en el alta. **Entonces:** la hoja avisa del posible duplicado y deja guardar igual. Un nombre idéntico (sin distinguir mayúsculas) se rechaza.
4. **Dado:** un material. **Cuando:** se lo quiere sacar. **Entonces:** solo se puede desactivar; deja de ofrecerse a las escuadrillas y se conserva en las órdenes que lo usaron.
5. **Dado:** el rol técnico. **Cuando:** consulta materiales. **Entonces:** ve nombre y unidad y nunca el precio.

## Decisiones tomadas en el refinamiento

Validadas con Gonza el 2026-11-02:

- **Una sola lista de materiales**, común a todas las escuadrillas. Sin stock por ahora (E08 queda para después).
- **Cada material tiene unidad** (kg, metro, unidad, litro). Es texto libre, con sugerencias.
- **Todos arrancan en $0**: administración completa los precios después (E02-06).
- **La lista inicial la pasa Gonza.** No se versiona (el repositorio es público): se carga con un script desde un CSV.
- El criterio 5 (lista sin precios para la escuadrilla) se entrega con E05-05, que la suma a las opciones del cierre.

## Notas técnicas

- Tabla `part` (`name` único con `lower(name)`, `unit` de hasta 20 caracteres con default `unidad`, `code` opcional, `is_active`). Migración `63b8f5e979d4`, junto con `part_price` (E02-06).
- `GET /admin/parts?include_inactive`, `POST /admin/parts` (crea también el precio 0), `PATCH /admin/parts/{id}` (nombre, unidad, activo). Solo administración. 409 `part_name_already_exists`; 404 `part_not_found`.
- `PartChoiceTechnicianOut` (id, nombre, unidad) para la escuadrilla, sin precio.
- Carga inicial: `python -m app.parts_import materiales.csv`, con columnas `nombre,unidad`. Saltea los que ya existen, así que se puede repetir.
- web-admin: hoja "Materiales y precios" en Catálogos (`features/parts/`), con buscador, "Mostrar desactivados" y el aviso de nombre parecido (sin mayúsculas, acentos ni espacios, comparado en el cliente).
