---
id: E11-02
title: "Importar equipos desde Persat"
epic: E11
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, datos]
depends_on: [E11-01, E03-03]
blocked_by: []
assumes: [D-002]
---

# E11-02 Importar equipos desde Persat

## Historia

**Como** administración, **quiero** importar los equipos desde la exportación de Persat, **para** no cargar a mano 200 a 1.000 equipos.

## Criterios de aceptación

1. **Dado:** un archivo de equipos. **Cuando:** se importa en modo prueba. **Entonces:** se muestra cuántos se crearían y cuáles no se pueden asociar a un cliente.
2. **Dado:** un equipo. **Cuando:** se importa. **Entonces:** queda asociado a su cliente y domicilio, conserva su código de Persat como código interno y su ubicación.
3. **Dado:** la importación. **Cuando:** se aplica. **Entonces:** cada equipo guarda su referencia al identificador de Persat.
4. **Dado:** una segunda importación. **Cuando:** se repite. **Entonces:** no duplica equipos.
5. **Dado:** un código de Persat repetido en más de un equipo. **Cuando:** se importa. **Entonces:** cada equipo repetido recibe un código nuevo generado por el sistema, conserva el de Persat como referencia y figura en el informe de calidad.
6. **Dado:** un equipo de Persat sin ubicación. **Cuando:** se importa. **Entonces:** queda con la ubicación "Sin ubicación" y figura en el informe de calidad.

## Fuera de alcance

- Informe de calidad completo (E11-04) y deshacer un lote (E11-05). Recortado el 2026-10-28 para la prueba del 2026-10-30.

## Notas técnicas

- Identificación según la propuesta de `D-002`. Unos 530 equipos de unos 55 clientes. Los códigos no son parejos (prefijos `EA` y `EH`, siglas de sector, formatos viejos y correlativos de 2 o 3 dígitos) y se importan tal cual, sin validarlos por largo ni formato.
- Lee la exportación cruda de Persat (`.xlsx`). Reglas de limpieza (tipo, subtipo, marca, gas, capacidad, tensión, columnas corridas) en `docs/domain/migracion-persat.md` (`D-010`). Verificación manual con la exportación del 2026-10-08: 532 equipos.
- Mismo comando que E11-01 (`--equipos`). El equipo va al primer domicilio activo de su cliente (cada cliente de Persat tiene uno). Sin cliente importado, la fila sale como error.
- El modelo no tiene campos para subtipo, función, capacidad, gas y tensión: van a `notes` en una línea ("Split. Frío/calor. 3000 frigorías. R-410A. 220 V."). La columna MODELO de Persat es la función, así que `model` queda vacío; el número de serie de Persat es el código interno, así que `serial_number` también.
- `legacy_id` = número de cliente + `/` + código de Persat (con `#2`, `#3` si se repite dentro del mismo cliente). Los repetidos se crean al final con el código que da la regla del sistema, y llevan "Código de Persat: ..." en las observaciones.
- Quedan para revisar, sin frenar la importación: tipo vacío (se toma como aire), gas con error de arrastre, sin ubicación, sin ningún dato y código repetido.
