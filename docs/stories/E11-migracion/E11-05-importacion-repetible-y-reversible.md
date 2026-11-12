---
id: E11-05
title: "Importación repetible y reversible"
epic: E11
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, datos]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E11-05 Importación repetible y reversible

## Historia

**Como** administración, **quiero** poder repetir una importación y deshacer un lote completo, **para** ensayar la migración sin riesgo hasta que esté bien.

## Criterios de aceptación

1. **Dado:** una importación. **Cuando:** se confirma. **Entonces:** queda registrada como un lote con fecha, usuario y cantidades.
2. **Dado:** un lote. **Cuando:** administración lo deshace. **Entonces:** se dan de baja (borrado lógico) todos los registros que creó y no se toca lo demás.
3. **Dado:** un lote que ya fue usado por órdenes nuevas. **Cuando:** se intenta deshacer. **Entonces:** se rechaza e indica por qué.
4. **Dado:** cada registro importado. **Cuando:** se consulta. **Entonces:** tiene su referencia de origen en `legacy_reference`.

## Notas técnicas

- No depende del formato de Persat: es la infraestructura de lotes.
- Los archivos de Persat y el de decisiones de migración se pasan por parámetro. Nunca se suben al repo: `persat-export/`, `*.xls` y `*.xlsx` están en `.gitignore` (salvo los archivos ficticios de `backend/tests/fixtures/`).

## Decisiones (2026-11-10)

- Las importaciones se corren por línea de comandos desde una máquina con los archivos: el lote guarda quién la corrió (`--por`) en vez de un usuario de la app.

## Hecho

- Tabla `import_batch` (fuente, quién, cuándo, resumen de cantidades, deshecho). Cada `legacy_reference` creada lleva su `batch_id`; la unicidad de las referencias ignora las de lotes deshechos, así se puede volver a importar.
- `--lotes` lista los lotes; `--deshacer <id>` da de baja (borrado lógico) las órdenes, equipos, clientes, domicilios, contactos y referencias del lote. Si hay órdenes nuevas sobre lo importado, no deshace nada y dice cuáles.
