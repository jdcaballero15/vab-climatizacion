---
id: E11-02
title: "Importar equipos desde Persat"
epic: E11
phase: 1
priority: must
status: draft
roles: [admin]
size: M
areas: [backend, datos]
depends_on: [E11-01, E03-03]
blocked_by: [D-002]
assumes: []
---

# E11-02 Importar equipos desde Persat

## Historia

**Como** administración, **quiero** importar los equipos desde la exportación de Persat, **para** no cargar a mano 200 a 1.000 equipos.

## Criterios de aceptación

1. **Dado:** un archivo de equipos. **Cuando:** se importa en modo prueba. **Entonces:** se muestra cuántos se crearían y cuáles no se pueden asociar a un cliente.
2. **Dado:** un equipo. **Cuando:** se importa. **Entonces:** queda asociado a su cliente y domicilio, con el identificador según `D-002`.
3. **Dado:** la importación. **Cuando:** se aplica. **Entonces:** cada equipo guarda su referencia al identificador de Persat.
4. **Dado:** una segunda importación. **Cuando:** se repite. **Entonces:** no duplica equipos.

## Notas técnicas

- Lee la exportación cruda de Persat (`.xlsx`). Reglas de limpieza (tipo, subtipo, marca, gas, capacidad, tensión, columnas corridas) en `docs/domain/migracion-persat.md` (`D-010`). Verificación manual con la exportación del 2026-10-08: 532 equipos.
