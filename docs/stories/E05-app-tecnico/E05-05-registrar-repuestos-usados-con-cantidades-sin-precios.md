---
id: E05-05
title: "Registrar repuestos usados con cantidades, sin precios"
epic: E05
phase: 1
priority: must
status: done
roles: [technician, admin]
size: L
areas: [backend, pwa, web-admin]
depends_on: [E05-04, E02-06]
blocked_by: []
assumes: []
---

# E05-05 Registrar repuestos usados con cantidades, sin precios

## Historia

**Como** escuadrilla, **quiero** elegir de la lista los materiales usados y cargar las cantidades, **para** que el precio de la orden se calcule con lo que se usó, sin que yo vea precios.

**Como** administración, **quiero** ver los materiales de cada orden con su precio y el total, corregirlos y aprobar la orden, **para** cobrar con el precio correcto y que no cambie después.

## Criterios de aceptación

1. **Dado:** un cierre, con cualquier resultado. **Cuando:** la escuadrilla agrega un material. **Entonces:** lo busca en la lista y ve solo nombre y unidad, y carga la cantidad (con decimales: 1,5 kg; 3,2 metros).
2. **Dado:** un material que no está en la lista. **Cuando:** la escuadrilla elige "Otro". **Entonces:** escribe qué material es y la cantidad.
3. **Dado:** una cantidad cero, negativa, no numérica o con más de tres decimales, un "Otro" sin texto, un material desactivado o repetido. **Cuando:** se intenta cerrar. **Entonces:** se rechaza con el motivo.
4. **Dado:** la app y la API del técnico. **Cuando:** se inspeccionan. **Entonces:** no exponen ningún precio, subtotal ni total (test de contrato).
5. **Dado:** una orden con materiales de una o varias visitas. **Cuando:** administración la mira. **Entonces:** ve cada material con su visita, cantidad, precio unitario y subtotal, y el total. "Otro" figura sin precio y no suma.
6. **Dado:** una orden sin aprobar. **Cuando:** administración corrige una cantidad, agrega o saca un material, o pasa un "Otro" a la lista. **Entonces:** se guarda, y queda en la línea de tiempo con quién y cuándo.
7. **Dado:** una orden sin aprobar. **Cuando:** cambia el precio de lista. **Entonces:** la orden toma el precio nuevo.
8. **Dado:** una orden terminada sin "Otro" pendientes. **Cuando:** administración la aprueba. **Entonces:** cada material queda con el precio vigente, y cambiar la lista después no la modifica. Desde ahí no se edita.
9. **Dado:** un reenvío del mismo cierre (E05-12). **Cuando:** llega. **Entonces:** no duplica materiales.

## Decisiones tomadas en el refinamiento

Validadas con Gonza el 2026-11-02:

- **Sin stock por ahora.** Se sacó la dependencia de E08-04: no se descuenta de camionetas ni depósitos.
- **El precio se congela al aprobar la orden**, no al cerrarla: los precios arrancan en $0 y se completan después (ver ADR 0005, ajuste del 2026-11-02, y la regla 4 de CLAUDE.md).
- **El total suma todas las visitas** ("requiere otra visita", "no se pudo hacer" y la final).
- **Administración corrige, agrega y saca** materiales antes de aprobar.
- **"Otro" lo pasa administración a la lista**: crea el material (con precio 0) y la línea pasa a ser ese material.
- **Fuera de alcance:** mano de obra calculada (E04-11) y stock (E08).

Decisiones de implementación (de MendoData, para revisar):

- No se aprueba con "Otro" pendientes (409 `other_materials_pending`).
- El mismo material dos veces en un cierre se rechaza (`part_repeated`): se suma la cantidad.
- Antes de aprobar, si hay materiales en $0 la pantalla avisa (no bloquea).

## Notas técnicas

- Tabla `part_usage` (`work_order_id`, `closure_id` nulo si lo agregó administración, `part_id` u `other_text`, `quantity NUMERIC(12,3) > 0`, `unit_price` nulo hasta aprobar, `created_by`, borrado lógico). Evento nuevo `materials_changed`, sin cambio de estado. Migración `0cf779285368`.
- Escuadrilla: `closure-options` trae `parts` (id, nombre, unidad); `ClosureCreate.parts` lleva las líneas (`extra="forbid"`: un precio de más es 422). El borrador local (E05-13) guarda los materiales; los borradores viejos vuelven sin materiales.
- Administración (`app/api/order_materials.py`): `GET /admin/orders/{id}/materials`, `POST .../materials`, `PATCH .../materials/{line}`, `POST .../materials/{line}/removal`, `POST .../materials/{line}/promotion`, `POST /admin/orders/{id}/approval`. La aprobación registra `review_approved` y estampa `unit_price`.
- `subtotal` y `price_updated_at` suman a `FORBIDDEN_TECHNICIAN_FIELDS`.
- pwa-tecnico: sección "Materiales usados" en el cierre (`ClosureMaterials.tsx`), con buscador y "Otro".
- web-admin: sección "Materiales" en "Ver cierre y cobro" (`OrderMaterials.tsx`), con corrección, alta, baja, "Pasar a la lista" y "Aprobar orden".
