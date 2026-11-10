---
id: E10-01
title: "Tablero: órdenes por estado"
epic: E10
phase: 1
priority: must
status: done
roles: [owner, admin]
size: M
areas: [backend, web-admin]
depends_on: [E04-05]
blocked_by: []
assumes: []
---

# E10-01 Tablero: órdenes por estado

## Historia

**Como** dirección, **quiero** ver cuántas órdenes hay en cada estado y cómo evolucionan, **para** saber cómo va el trabajo de un vistazo.

## Criterios de aceptación

1. **Dado:** órdenes en varios estados. **Cuando:** abro el tablero. **Entonces:** veo la cantidad por estado y una evolución por semana o mes.
2. **Dado:** el tablero. **Cuando:** selecciono un estado. **Entonces:** llego a la lista de esas órdenes.
3. **Dado:** los datos. **Cuando:** se calculan. **Entonces:** coinciden con el panel de órdenes (E04-05).

## Notas técnicas

- Reemplaza a la opción "tablero en Power BI" de la propuesta original. Si más adelante se quiere Power BI, se expone una vista de datos de solo lectura.

## Hecho

- `GET /admin/dashboard` (administración y dirección; el técnico recibe 403) devuelve todas las secciones con los mismos filtros: período (por defecto los últimos 30 días), cliente, escuadrilla, tipo de trabajo y tipo de equipo. Sin precios.
- Las cantidades por estado salen de la misma consulta que el panel de órdenes (E04-05), así coinciden; cada una lleva a `/ordenes?estado=...`. Evolución: creadas y terminadas por semana (lunes a domingo), en barras con leyenda, valor al pasar o enfocar y vista de tabla.
