---
id: E02-08
title: "Importar y exportar catálogos por CSV"
epic: E02
phase: 1
priority: could
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E02-01, E02-05]
blocked_by: []
assumes: [D-003]
---

# E02-08 Importar y exportar catálogos por CSV

## Historia

**Como** administración, **quiero** cargar o descargar un catálogo completo desde un archivo CSV, **para** hacer cargas masivas iniciales y revisarlas en una planilla.

## Criterios de aceptación

1. **Dado:** un archivo CSV válido. **Cuando:** administración lo importa. **Entonces:** se muestra una vista previa con altas, cambios y errores antes de confirmar.
2. **Dado:** una fila con errores. **Cuando:** se importa. **Entonces:** se informa el número de fila y el motivo, y no se aplica nada hasta corregir.
3. **Dado:** un catálogo. **Cuando:** administración lo exporta. **Entonces:** descarga un CSV con las mismas columnas que acepta la importación.

## Notas técnicas

- Los CSV con datos reales no se suben al repositorio (ver `.gitignore`).

## Decisiones (2026-11-10)

- No se pidió D-003 para esto: el CSV usa los mismos nombres que la pantalla.

## Hecho

- Tipos de trabajo, tipos de equipo, fallas, reparaciones y materiales (sin precios: tienen su historial aparte). `GET /admin/catalog-csv/{catálogo}` exporta; `POST .../preview` muestra altas, cambios, sin cambios y errores con su fila; `POST .../apply` aplica todo en una transacción o, con algún error, nada.
- Se compara por nombre sin mayúsculas ni espacios de más (y por tipo de equipo y falla en fallas y reparaciones). "activo" acepta sí o no.
- web-admin: "Importar y exportar" en Catálogos.
