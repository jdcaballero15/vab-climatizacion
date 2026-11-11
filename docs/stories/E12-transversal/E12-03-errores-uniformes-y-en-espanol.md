---
id: E12-03
title: "Errores uniformes y en español"
epic: E12
phase: 1
priority: must
status: done
roles: [admin, technician, owner]
size: S
areas: [backend, web-admin, pwa]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E12-03 Errores uniformes y en español

## Historia

**Como** usuario del sistema, **quiero** recibir mensajes de error claros y en español, **para** entender qué pasó y qué hacer.

## Criterios de aceptación

1. **Dado:** un error de validación. **Cuando:** ocurre. **Entonces:** la API responde `{code, message}` y, si aplica, el detalle por campo.
2. **Dado:** un error inesperado. **Cuando:** ocurre. **Entonces:** el usuario ve un mensaje genérico y el detalle técnico va solo al log.
3. **Dado:** los mensajes de error. **Cuando:** se revisan. **Entonces:** no incluyen datos personales ni detalles internos.

## Hecho

- `app/core/errors.py`: los 422 de validación vienen como `{code: "validation_error", message, field, fields: [{field, message}]}` en español; un error inesperado devuelve 500 `internal_error` con un mensaje genérico y deja el detalle en el log con solo el método y la ruta.
- Los errores propios ya usaban `{code, message}`.
