---
id: E11-04
title: "Informe de calidad de datos de la importación"
epic: E11
phase: 1
priority: should
status: draft
roles: [admin]
size: M
areas: [backend, datos]
depends_on: [E11-01]
blocked_by: []
assumes: []
---

# E11-04 Informe de calidad de datos de la importación

## Historia

**Como** administración, **quiero** recibir un informe de los problemas de la importación (duplicados, equipos sin cliente, fechas inválidas), **para** corregir los datos antes de usarlos.

## Criterios de aceptación

1. **Dado:** una importación en modo prueba. **Cuando:** termina. **Entonces:** se descarga un informe con cada problema, su fila y una sugerencia.
2. **Dado:** los duplicados probables. **Cuando:** se detectan. **Entonces:** se agrupan para decidir si se unifican.
3. **Dado:** el informe. **Cuando:** se genera. **Entonces:** no incluye datos fuera de los del archivo importado.

## Notas técnicas

- Los problemas a informar salen de las reglas de `docs/domain/migracion-persat.md`: registros que no se migran, códigos corregidos, sin dirección, sin ubicación, tipo asumido, gas corregido, columnas corridas, códigos repetidos y servicios repetidos.
