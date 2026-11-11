---
id: E04-11
title: "Registrar mano de obra y otros cargos de una orden"
epic: E04
phase: 1
priority: should
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E04-06, E00-04]
blocked_by: []
assumes: []
---

# E04-11 Registrar mano de obra y otros cargos de una orden

## Historia

**Como** administración, **quiero** registrar la mano de obra y otros cargos de una orden y ver el total junto con los repuestos, **para** preparar la facturación con los importes correctos.

## Criterios de aceptación

1. **Dado:** una orden cerrada. **Cuando:** administración agrega un cargo (mano de obra, visita u otro) con concepto e importe. **Entonces:** se guarda como un registro de cargo con usuario y fecha.
2. **Dado:** una orden con repuestos usados. **Cuando:** administración ve el total. **Entonces:** suma los repuestos al precio estampado y los cargos registrados.
3. **Dado:** el rol técnico. **Cuando:** consulta cualquier orden. **Entonces:** no hay ningún cargo, importe ni total en la respuesta.
4. **Dado:** un cargo. **Cuando:** se edita o se anula. **Entonces:** queda en la auditoría.

## Decisiones (Gonza, 2026-11-10)

- La mano de obra se sigue cargando a mano (sin cálculo por lista, abono o presupuesto).
- Además hay "otros cargos" con descripción e importe.

## Hecho

- Tabla `work_order_charge` con borrado lógico. `GET/POST /admin/orders/{id}/charges`, `PUT/DELETE /admin/orders/{id}/charges/{charge_id}`; cada alta, corrección o baja deja `charges_changed` con el antes y el después.
- `GET /admin/orders/{id}/billing` devuelve repuestos, mano de obra, otros cargos, total, factura y cobro. Nada de esto llega al técnico (campos en `FORBIDDEN_TECHNICIAN_FIELDS`).
