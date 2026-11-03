---
id: E03-06
title: "Buscar clientes y equipos"
epic: E03
phase: 1
priority: must
status: done
roles: [admin, owner]
size: S
areas: [backend, web-admin]
depends_on: [E03-01]
blocked_by: []
assumes: []
---

# E03-06 Buscar clientes y equipos

## Historia

**Como** administración, **quiero** buscar clientes y equipos por nombre, dirección o identificador, **para** encontrar rápido a quién me llama por teléfono.

## Criterios de aceptación

1. **Dado:** un texto de búsqueda. **Cuando:** busco. **Entonces:** obtengo coincidencias de clientes y equipos tolerando mayúsculas, acentos y errores menores.
2. **Dado:** miles de registros. **Cuando:** busco. **Entonces:** la respuesta tarda menos de 500 ms en el entorno de producción.
3. **Dado:** un registro dado de baja. **Cuando:** busco. **Entonces:** no aparece salvo que active "ver bajas".

## Notas técnicas

- Postgres con `pg_trgm`. Sin límites de delegación como en Power Apps.

## Refinamiento y avance

Acordado con Gonza el 2026-11-03 y hecho el mismo día:

- Una caja de búsqueda arriba de Clientes. Encuentra clientes por nombre, número, dirección o rótulo de sus domicilios y teléfono de sus contactos, y equipos por código, número de serie, marca, modelo, ubicación o tipo, con su cliente y domicilio. Tocar un resultado abre la ficha del cliente (y la trae a la vista).
- `GET /admin/search?q=&include_deleted=` (administración y dirección; técnico 403; desde 2 letras): hasta 10 clientes y 10 equipos. Cada palabra tiene que estar en algún dato, sin mayúsculas ni acentos (el `translate` de siempre, sin la extensión `unaccent`). Si no, alcanza con que se parezca (`word_similarity` de `pg_trgm` desde 0,5, migración `22c25d75ac2c`), salvo que la búsqueda tenga números: "10643" no trae "10642". Un teléfono se busca solo por sus números ("421-5566" encuentra "(0385) 421 5566"). Primero las que contienen todas las palabras, después las más parecidas.
- Criterio 2: con 5000 clientes y 5000 equipos ficticios en la base local, entre 90 y 250 ms por búsqueda (sin índices de trigramas; si hiciera falta, un índice GIN sobre los textos).
- Criterio 3: "dado de baja" es el borrado lógico; las bajas aparecen con "Incluir bajas" y marcadas.
- Fuera de esta historia: el selector de cliente de la orden nueva sigue buscando como antes (nombre o número).
