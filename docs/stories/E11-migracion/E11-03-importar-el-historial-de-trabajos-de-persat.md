---
id: E11-03
title: "Importar el historial de trabajos de Persat"
epic: E11
phase: 1
priority: must
status: draft
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
