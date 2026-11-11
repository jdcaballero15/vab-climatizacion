---
id: E02-07
title: "Promover un texto de \"Otro\" a la lista"
epic: E02
phase: 1
priority: should
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E02-03, E02-04, E05-04]
blocked_by: []
assumes: []
---

# E02-07 Promover un texto de "Otro" a la lista

## Historia

**Como** administración, **quiero** ver los textos más repetidos que los técnicos escribieron en "Otro" y sumarlos a la lista de fallas o reparaciones, **para** que los catálogos crezcan con lo que realmente pasa en campo.

## Criterios de aceptación

1. **Dado:** textos libres cargados en "Otro". **Cuando:** administración abre la pantalla de revisión. **Entonces:** ve cada texto con su cantidad de repeticiones, agrupando variantes simples (mayúsculas, espacios).
2. **Dado:** un texto repetido. **Cuando:** administración lo promueve. **Entonces:** se crea el valor de catálogo y las órdenes anteriores con ese texto pasan a referenciarlo.
3. **Dado:** un texto. **Cuando:** administración lo descarta. **Entonces:** deja de mostrarse en la revisión pero se conserva en la orden.

## Notas técnicas

- La propuesta al cliente dice: "lo que se repite se suma a la lista".
- Para **materiales** ya se hizo una versión por orden con E05-05: en la orden, administración toca "Pasar a la lista" en una línea "Otro", se crea el material y esa línea pasa a referenciarlo. Falta la pantalla de textos repetidos (para fallas, reparaciones y materiales).

## Hecho

- `GET /admin/other-texts?kind=failure|repair|part`: los textos de "Otro" agrupados sin mayúsculas ni espacios de más, con sus repeticiones, el más repetido primero.
- `POST /admin/other-texts/promote`: crea el valor (una reparación nueva pide su falla) o usa uno existente (`target_id`), y las órdenes con ese texto pasan a referenciarlo. `POST /admin/other-texts/dismiss`: deja de mostrarse (`dismissed_other_text`); la orden conserva el texto.
- web-admin: "Textos de «Otro»" en Catálogos.
