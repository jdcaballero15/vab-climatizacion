---
id: E07-01
title: "Gestionar plantillas de checklist por frecuencia y tipo de equipo"
epic: E07
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E02-02, E01-04]
blocked_by: []
assumes: []
---

# E07-01 Gestionar plantillas de checklist por frecuencia y tipo de equipo

## Historia

**Como** administración, **quiero** editar el checklist de mantenimiento, **para** que cada orden de mantenimiento llegue al técnico con los pasos que corresponden.

## Lo acordado

Decisión de Gonza (2026-11-03): **un checklist único** para todo mantenimiento, editable por la oficina. Sin plantillas por frecuencia ni por tipo de equipo. Cada paso se marca OK o No OK (E07-06); las mediciones con rango (E07-02) quedan para más adelante. Como el cliente todavía no pasó su checklist real, se arranca con 6 pasos típicos que la oficina corrige.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** agrega un paso. **Entonces:** va al final de la lista y entra en las órdenes que se generen desde ese momento.
2. **Dado:** el checklist. **Cuando:** administración sube o baja un paso. **Entonces:** las órdenes nuevas lo traen en ese orden. Si la lista cambió mientras tanto (otra pestaña), se rechaza y pide recargar.
3. **Dado:** un paso editado. **Cuando:** hay órdenes ya generadas. **Entonces:** esas órdenes conservan los pasos con que se generaron.
4. **Dado:** un paso. **Cuando:** se quita. **Entonces:** se desactiva, no se borra, y deja de copiarse a las órdenes nuevas. Reactivado vuelve al final.
5. **Dado:** el rol técnico. **Cuando:** intenta ver o editar el checklist. **Entonces:** recibe acceso denegado.
6. **Dado:** un nombre que ya tiene otro paso (activo o no). **Cuando:** se guarda. **Entonces:** se rechaza (409).

## Notas técnicas

- Tablas `maintenance_check_step` (la lista) y `work_order_check_item` (la copia de cada orden, con el nombre). Migración `a968d70ec211`: carga los 6 pasos iniciales y copia el checklist a las órdenes de mantenimiento ya generadas y abiertas.
- API: `GET/POST /admin/maintenance/check-steps`, `PATCH /admin/maintenance/check-steps/{id}`, `PUT /admin/maintenance/check-steps/order` (todos los activos en el orden nuevo).
- Web-admin: botón "Checklist" en Mantenimiento, con alta, renombrar, desactivar, subir y bajar.
- La generación (E07-04) copia los pasos activos al crear cada orden.
