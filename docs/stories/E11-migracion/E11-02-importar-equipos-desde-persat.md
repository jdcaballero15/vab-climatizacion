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
blocked_by: [D-010]
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

## Notas técnicas

- Identificación según la propuesta de `D-002`. Unos 530 equipos de unos 55 clientes; los formatos de código no son parejos (varios prefijos) y se importan tal cual.
