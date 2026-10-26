---
id: E11-06
title: "Cargar los abonados y los equipos de cada abono"
epic: E11
phase: 1
priority: must
status: draft
roles: [admin]
size: M
areas: [backend, datos]
depends_on: [E07-03, E11-02, E11-05]
blocked_by: []
assumes: [D-002]
---

# E11-06 Cargar los abonados y los equipos de cada abono

## Historia

**Como** administración, **quiero** cargar el listado de clientes abonados y los equipos incluidos en cada abono, **para** que el mantenimiento mensual se genere desde el primer mes.

## Criterios de aceptación

1. **Dado:** un archivo con clientes abonados y sus equipos. **Cuando:** se importa en modo prueba. **Entonces:** se muestran los abonos que se crearían y los equipos que no se encuentran.
2. **Dado:** la importación. **Cuando:** se aplica. **Entonces:** se crean los abonos con sus equipos, frecuencia y fecha de inicio.
3. **Dado:** un equipo no encontrado. **Cuando:** se importa. **Entonces:** queda en un informe de pendientes para resolver.
