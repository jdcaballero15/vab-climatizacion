---
id: E06-01
title: "Crear una orden de taller desde la oficina"
epic: E06
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E04-02]
blocked_by: []
assumes: []
---

# E06-01 Crear una orden de taller desde la oficina

## Historia

**Como** administración, **quiero** crear una orden de taller con retiro, taller y devolución como etapas de una sola orden, **para** tener un solo registro por equipo que se lleva al galpón, y facturarlo una vez.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea una orden de tipo taller. **Entonces:** se generan las etapas retiro, taller y devolución en ese orden.
2. **Dado:** una orden de taller. **Cuando:** se consulta. **Entonces:** es una única orden con tres etapas y un solo número.
3. **Dado:** una orden de taller. **Cuando:** se factura. **Entonces:** se factura una sola vez al terminar la última etapa.

## Notas técnicas

- Ver ADR 0007.

## Refinamiento y avance

Acordado con Gonza el 2026-11-03 (escuadrillas en todo, firma y nombre sin DNI, nace desde la visita y desde la oficina, PDF más adelante, etapas en fila: opción A del ADR 0007) y hecho el mismo día:

- En "Nueva orden", "Tipo de orden": En el lugar o Taller. La de taller arranca en el retiro (`kind = workshop`, `workshop_stage = pickup`) y es una sola orden con un solo número.
