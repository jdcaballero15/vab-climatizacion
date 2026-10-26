---
id: E11-01
title: "Importar clientes desde Persat"
epic: E11
phase: 1
priority: must
status: draft
roles: [admin]
size: M
areas: [backend, datos]
depends_on: [E03-01, E11-05]
blocked_by: []
assumes: []
---

# E11-01 Importar clientes desde Persat

## Historia

**Como** administración, **quiero** importar los clientes desde la exportación de Persat, **para** no cargar a mano unos 640 clientes.

## Criterios de aceptación

1. **Dado:** un archivo de exportación válido. **Cuando:** se importa en modo prueba. **Entonces:** se muestra cuántos clientes se crearían, cuáles ya existen y cuáles tienen errores, sin guardar nada.
2. **Dado:** la confirmación. **Cuando:** se aplica. **Entonces:** se crean los clientes y cada uno guarda su referencia al identificador de Persat.
3. **Dado:** una segunda importación del mismo archivo. **Cuando:** se ejecuta. **Entonces:** no crea duplicados.
4. **Dado:** una fila con datos inválidos. **Cuando:** se importa. **Entonces:** se informa con su número y el motivo.
5. **Dado:** un registro interno o de prueba de Persat (operario, depósito, administración). **Cuando:** se importa. **Entonces:** no se migra y figura en el informe.
6. **Dado:** un archivo de decisiones de migración. **Cuando:** se pasa al importar. **Entonces:** se aplican sus decisiones (registros que no se migran, clientes a unificar); si no se pasa, la importación funciona igual.

## Notas técnicas

- Lee la exportación cruda de Persat (`.xlsx`), no la planilla limpia. Reglas de limpieza en `docs/domain/migracion-persat.md` (`D-010`). El archivo de Persat y el de decisiones se pasan por parámetro y nunca se suben al repo.
- Campos que entran y cómo se reparte la columna Descripción (CUIT, condición fiscal, referencia): ver E03-01 y `docs/domain/migracion-persat.md`. El cliente sin número se resuelve con el archivo de decisiones de migración.
- Verificación manual con la exportación del 2026-10-08: 632 clientes. Los tests usan archivos ficticios.
