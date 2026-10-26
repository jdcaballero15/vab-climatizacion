---
id: E03-01
title: "Alta y edición de clientes"
epic: E03
phase: 1
priority: must
status: draft
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E01-04]
blocked_by: []
assumes: [D-002]
---

# E03-01 Alta y edición de clientes

## Historia

**Como** administración, **quiero** dar de alta y editar clientes con sus datos de contacto, **para** tener a cada cliente identificado y asociarle todos sus trabajos.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un cliente con nombre y al menos un contacto. **Entonces:** queda disponible para crear órdenes.
2. **Dado:** un cliente. **Cuando:** tiene varios contactos. **Entonces:** uno o más pueden marcarse para recibir el informe mensual.
3. **Dado:** un cliente con nombre muy parecido a otro. **Cuando:** se guarda. **Entonces:** el sistema advierte del posible duplicado.
4. **Dado:** un cliente. **Cuando:** se edita. **Entonces:** el cambio queda en la auditoría.
5. **Dado:** el rol técnico. **Cuando:** llama a la API de clientes de administración. **Entonces:** recibe acceso denegado.

## Notas técnicas

- Entre 50 y 200 clientes. CUIT o DNI del cliente es dato personal (ver `SECURITY.md`).
- Cada cliente tiene un número único (`client.number`, texto) que forma parte del código de sus equipos (`D-002`). En los clientes nuevos lo asigna el sistema siguiendo la serie numérica (el siguiente al máximo); en los migrados se toma el de Persat tal cual (E11-01), que mezcla series.
