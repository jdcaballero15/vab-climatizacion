---
id: E00-04
title: "Test de contrato: el técnico no ve precios"
epic: E00
phase: 1
priority: must
status: done
roles: [dev]
size: S
areas: [backend]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E00-04 Test de contrato: el técnico no ve precios

## Historia

**Como** equipo de desarrollo, **quiero** un test automático que recorra los esquemas de respuesta del técnico y falle si aparece un campo de precio, mano de obra o historial, **para** garantizar que la regla de visibilidad no se rompe sin que nadie lo note.

## Criterios de aceptación

1. **Dado:** los esquemas `*TechnicianOut`. **Cuando:** corre el test de contrato. **Entonces:** falla si algún campo (a cualquier profundidad) coincide con la lista de campos prohibidos.
2. **Dado:** la lista de campos prohibidos. **Cuando:** se agrega un campo nuevo sensible. **Entonces:** se edita en un solo archivo versionado y el test lo toma.
3. **Dado:** una ruta bajo `/tech/`. **Cuando:** la ruta devuelve un esquema que no termina en `TechnicianOut`. **Entonces:** el test falla.
4. **Dado:** el workflow de CI. **Cuando:** el test de contrato falla. **Entonces:** el check `ci-ok` queda en rojo.

## Notas técnicas

- Ver ADR 0006. Campos prohibidos iniciales: `price`, `unit_price`, `list_price`, `amount`, `charge`, `total`, y todo lo bajo `history`.
- También debe cubrir los esquemas de error, para que no filtren datos.

## Notas de implementación

- Lista de campos prohibidos en un solo archivo versionado: `app/core/sensitive_fields.py` (`FORBIDDEN_TECHNICIAN_FIELDS`). Al sumar un campo sensible nuevo, se edita solo ahí.
- Test de contrato en `backend/tests/test_technician_contract.py`:
  - Descubre todos los esquemas `*TechnicianOut` definidos en `app` (importa los submódulos y recorre las subclases de `BaseModel`) y falla si alguno expone un campo prohibido a cualquier profundidad, incluidos modelos anidados (criterios 1 y 2).
  - Verifica que toda ruta bajo `/tech/` declare un esquema de respuesta `*TechnicianOut` (criterio 3).
  - Escanea también los esquemas de error de las rutas `/tech/` (nota del ADR).
  - Incluye fixtures que prueban que el detector atrapa un campo prohibido anidado, para que el contrato no sea un no-op mientras todavía no hay esquemas del técnico.
- El test corre en el job `backend` del CI, del que depende `ci-ok`: si el contrato falla, `ci-ok` queda en rojo (criterio 4).
- Todavía no existen esquemas `*TechnicianOut` ni rutas `/tech/` (los agregan historias posteriores); el test pasa en vacío y se activa a medida que se agreguen.
