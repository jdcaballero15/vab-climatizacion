---
id: E03-03
title: "Alta y edición de equipos"
epic: E03
phase: 1
priority: must
status: draft
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-02, E02-02]
blocked_by: []
assumes: [D-002]
---

# E03-03 Alta y edición de equipos

## Historia

**Como** administración, **quiero** dar de alta y editar los equipos de un cliente, **para** tener el parque de equipos para asociar trabajos e historial.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un equipo con domicilio, ubicación y tipo. **Entonces:** queda asociado al cliente y disponible para órdenes. Marca, modelo y el resto de los datos son opcionales.
2. **Dado:** un equipo nuevo. **Cuando:** se guarda. **Entonces:** el sistema le genera el código interno (prefijo según el tipo + número de cliente + correlativo) y no se puede escribir a mano.
3. **Dado:** un equipo. **Cuando:** se quiere eliminar. **Entonces:** solo se puede dar de baja lógica y conserva su historial.
4. **Dado:** un código interno que ya existe en cualquier cliente. **Cuando:** se guarda. **Entonces:** se rechaza.
5. **Dado:** un equipo. **Cuando:** se le cambia la ubicación. **Entonces:** conserva su código y su historial.
6. **Dado:** el rol técnico. **Cuando:** llama a la API de equipos de administración. **Entonces:** recibe acceso denegado.
7. **Dado:** un cliente que ya tiene 99 equipos. **Cuando:** se da de alta el siguiente. **Entonces:** el correlativo pasa a `100`.

## Notas técnicas

- Identificación según la propuesta de `D-002`: `internal_code` único en toda la empresa y generado por el sistema, `location_note` obligatoria y sin unicidad (dos equipos pueden compartir ubicación). Unos 530 equipos en Persat.
- El código es texto sin largo fijo: no validarlo por largo ni por formato. Prefijo `EA` para aire acondicionado y `EH` para heladera; el resto de los tipos, pendiente en `D-002`. Si el código generado ya existe, se prueba el siguiente correlativo.
- El código usa el número de cliente (`client.number`, E03-01).
