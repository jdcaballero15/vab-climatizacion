---
id: E08-01
title: "Gestionar depósitos y camionetas"
epic: E08
phase: 1
priority: must
status: draft
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E01-04]
blocked_by: []
assumes: []
---

# E08-01 Gestionar depósitos y camionetas

## Historia

**Como** administración, **quiero** dar de alta los depósitos y las camionetas (con su escuadrilla), **para** saber dónde está cada repuesto.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un depósito o una camioneta con nombre. **Entonces:** queda disponible como ubicación de stock.
2. **Dado:** una camioneta. **Cuando:** se asocia a una escuadrilla. **Entonces:** los usos de repuestos de esa escuadrilla descuentan de esa camioneta.
3. **Dado:** una ubicación con movimientos. **Cuando:** se quiere eliminar. **Entonces:** solo se puede desactivar.

## Preguntas abiertas

- ¿Cuántos depósitos hay? ¿Cada escuadrilla anda siempre en la misma camioneta (D-013)? Si es así, la camioneta podría ser un dato de la escuadrilla.
