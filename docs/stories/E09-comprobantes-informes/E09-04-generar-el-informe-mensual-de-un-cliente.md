---
id: E09-04
title: "Generar el informe mensual de un cliente"
epic: E09
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend]
depends_on: [E04-06]
blocked_by: []
assumes: []
---

# E09-04 Generar el informe mensual de un cliente

## Historia

**Como** administración, **quiero** que el sistema arme el informe mensual de cada cliente con los trabajos realizados, **para** darle al cliente el historial sin construirle un portal.

## Criterios de aceptación

1. **Dado:** un cliente con trabajos en el mes. **Cuando:** se genera el informe. **Entonces:** lista cada trabajo con fecha, equipo, tipo, falla y reparación.
2. **Dado:** un cliente sin trabajos en el mes. **Cuando:** se genera. **Entonces:** no se envía informe vacío.
3. **Dado:** el informe. **Cuando:** se genera. **Entonces:** no incluye datos de otros clientes.
4. **Dado:** un mismo período. **Cuando:** se genera dos veces. **Entonces:** produce el mismo contenido.

## Decisiones (Gonza)

- Sin precios. Incluye las órdenes del mes (y con ellas los mantenimientos, con su tipo de trabajo); no hay mediciones (pasaron al icebox). El envío por mail es E09-05, que espera el proveedor de mail (E00-10).

## Hecho

- `GET /admin/clients/{id}/monthly-report?year=&month=` (administración y dirección) devuelve el PDF con las órdenes del cliente que pasaron a Terminada en ese mes: fecha, número, equipo, tipo, falla y reparación. Sin trabajos, 409 `empty_report` (criterio 2). Solo órdenes del cliente (criterio 3). La fecha del PDF es el fin del período, así el mismo mes da el mismo archivo (criterio 4).
- web-admin: "Informe de trabajos del mes" en la ficha del cliente, con el mes y "Descargar PDF".
