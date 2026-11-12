---
id: E11-03
title: "Importar el historial de trabajos de Persat"
epic: E11
phase: 1
priority: must
status: done
roles: [admin]
size: L
areas: [backend, datos]
depends_on: [E11-02, E04-06]
blocked_by: []
assumes: []
---

# E11-03 Importar el historial de trabajos de Persat

## Historia

**Como** administración, **quiero** importar el historial de trabajos de Persat, **para** poder mostrar el historial de cada cliente y equipo desde el primer día.

## Criterios de aceptación

1. **Dado:** un archivo de historial. **Cuando:** se importa en modo prueba. **Entonces:** se muestra cuántos trabajos se importarían y a qué clientes y equipos se asocian.
2. **Dado:** un trabajo importado. **Cuando:** se consulta. **Entonces:** figura en el historial del cliente y del equipo marcado como "importado desde Persat".
3. **Dado:** los trabajos importados. **Cuando:** se consultan. **Entonces:** no se mezclan con las estadísticas del sistema nuevo salvo que se pida explícitamente.
4. **Dado:** el historial importado. **Cuando:** se ve. **Entonces:** es de solo lectura.

## Notas técnicas

- Se sumó al alcance: originalmente estaba fuera. El cliente confirmó que Persat es exportable.

- Lee los archivos de órdenes de Persat, uno por formulario: `.xls` que en realidad son HTML, con tablas anidadas en algunas celdas. Reglas en `docs/domain/migracion-persat.md` (`D-010`).
- Por orden se toma: número de Persat, tipo de trabajo (según el formulario), fecha, estado de Persat, cliente, cuadrilla, técnicos, código de equipo (si no es `N/A`) y un detalle de texto que junta reclamo, observación, trabajo realizado y falla detectada.
- Verificación manual con la exportación del 2026-10-08: 1.743 órdenes. Los tests usan archivos ficticios con el mismo formato.

## Preguntas abiertas

- Respondida (cliente, 2026-10-28): falla y reparación de Persat quedan como texto, tal cual las escribieron los técnicos, en la ficha del cliente. Le alcanza así para consultar.
- En casi 9 de cada 10 reparaciones no hay código de equipo: esas órdenes quedan en el historial del cliente pero no en el de un equipo.

## Decisiones (2026-11-10)

- Cada orden de Persat es una orden con `source = persat`: Cancelada si en Persat estaba cancelada; Terminada en cualquier otro caso. El estado de Persat, la cuadrilla, los técnicos y el detalle quedan como texto en la descripción (no se crean escuadrillas ni técnicos).
- La fecha de Persat es la del evento de creación. Un tipo de trabajo que no existe se crea desactivado (no se ofrece para órdenes nuevas).

## Hecho

- `python -m app.persat_import --ordenes <carpeta>` lee los `.xls` (HTML) con el parser de la biblioteca estándar, sin dependencias nuevas (`app/services/persat_orders.py`). En prueba informa cuántas, de cuántos clientes, cuántas con equipo y por tipo de trabajo.
- El equipo sale de la celda de datos del equipo o de "NUMERO DE EQUIPO", si es un código importado (referencia "cliente/código").
- Las importadas no entran en el panel de órdenes (criterio 3) y no se modifican: cambiar el estado o el equipo da 409 `imported_order_read_only` (criterio 4). En el historial del cliente vienen con `imported` y su detalle; la ficha del equipo (E03-05) las marca.
- Verificado a mano contra la exportación del 2026-10-08, en una base aparte y en modo prueba: 632 clientes, 532 equipos y 1.743 órdenes (653 con equipo), sin errores.
