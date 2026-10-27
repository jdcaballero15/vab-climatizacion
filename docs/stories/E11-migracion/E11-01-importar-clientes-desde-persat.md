---
id: E11-01
title: "Importar clientes desde Persat"
epic: E11
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, datos]
depends_on: [E03-01]
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

## Fuera de alcance

Recortado el 2026-10-28 para la prueba del cliente con datos reales del 2026-10-30:

- El archivo de decisiones de migración (registros puntuales que no se migran, clientes a unificar): queda para cuando haga falta. Sin él, la importación aplica solo las reglas generales.
- Deshacer un lote y registrar lotes con usuario y cantidades: E11-05. La repetición sin duplicar sí está acá, con `legacy_reference`.
- El informe de calidad completo: E11-04. Acá el informe es el de la línea de comandos.
- Una pantalla para importar: se corre por línea de comandos.

## Notas técnicas

- Lee la exportación cruda de Persat (`.xlsx`), no la planilla limpia. Reglas de limpieza en `docs/domain/migracion-persat.md` (`D-010`). El archivo de Persat y el de decisiones se pasan por parámetro y nunca se suben al repo.
- Campos que entran y cómo se reparte la columna Descripción (CUIT, condición fiscal, referencia): ver E03-01 y `docs/domain/migracion-persat.md`. El cliente sin número se resuelve con el archivo de decisiones de migración.
- Verificación manual con la exportación del 2026-10-08: 632 clientes. Los tests usan archivos ficticios.
- Línea de comandos: `python -m app.persat_import --clientes <xlsx> [--equipos <xlsx>] [--aplicar]`. Sin `--aplicar` es el modo prueba: hace todo en una transacción y la deshace, así las cantidades y los números asignados son los mismos que daría la importación real. El informe muestra fila, número de cliente y motivo, sin nombres ni contactos.
- Reglas puras en `app/domain/persat.py`; lectura, transacción e informe en `app/services/persat_import.py`. Referencia en `legacy_reference` (migración `d9f1b3a7c520`): `entity = client`, `legacy_id` = número de cliente normalizado (o `sin-numero:` + razón social para el que no tiene).
- Registro de prueba: el nombre dice "Persat", "prueba" o "test" como palabra completa (hay apellidos reales que empiezan con "Test").
- Un cliente cargado a mano con el mismo número no se pisa: la fila sale como error.
- El cliente sin número recibe el siguiente de la serie numérica del sistema, después de importar los demás, y queda para revisar.
