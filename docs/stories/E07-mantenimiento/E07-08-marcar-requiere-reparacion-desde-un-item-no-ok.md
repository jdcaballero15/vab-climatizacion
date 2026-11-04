---
id: E07-08
title: "Marcar \"requiere reparación\" desde un ítem No OK"
epic: E07
phase: 1
priority: must
status: done
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E07-06, E05-04]
blocked_by: []
assumes: []
---

# E07-08 Marcar "requiere reparación" desde un ítem No OK

## Historia

**Como** técnico, **quiero** marcar que algo requiere reparación cuando un paso da No OK y seguir en la misma orden, **para** resolver el problema sin que administración tenga que crear otra orden.

## Criterios de aceptación

1. **Dado:** un paso en No OK. **Cuando:** marco "requiere reparación". **Entonces:** la orden de mantenimiento pasa a pedir falla y reparación como un cierre normal.
2. **Dado:** la orden. **Cuando:** se cierra. **Entonces:** conserva el checklist y la falla y reparación registradas.
3. **Dado:** una orden con "requiere reparación". **Cuando:** administración la revisa. **Entonces:** ve ambas partes en el mismo detalle.
4. **Dado:** un paso en OK. **Cuando:** llega con "requiere reparación" u observación. **Entonces:** se rechaza.

## Notas técnicas

- `work_order_closure_check.requires_repair`, con CHECK: solo en No OK.
- El detalle del cierre (`GET /admin/orders/{id}/closure`) trae `checklist` con nombre, resultado, observación y si requiere reparación; web-admin lo muestra junto a la falla y la reparación.
