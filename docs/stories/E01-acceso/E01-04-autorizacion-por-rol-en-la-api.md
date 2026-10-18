---
id: E01-04
title: "Autorización por rol en la API"
epic: E01
phase: 1
priority: must
status: done
roles: [admin, technician, owner]
size: M
areas: [backend]
depends_on: [E01-01, E00-04]
blocked_by: []
assumes: []
---

# E01-04 Autorización por rol en la API

## Historia

**Como** dirección, **quiero** que cada rol solo pueda hacer y ver lo permitido por la matriz de permisos, **para** proteger la información sensible aunque alguien manipule la aplicación.

## Criterios de aceptación

1. **Dado:** una ruta de la API. **Cuando:** se declara. **Entonces:** exige explícitamente uno o más roles mediante una dependencia común.
2. **Dado:** un técnico. **Cuando:** pide una orden que no tiene asignada, por su ID. **Entonces:** recibe 404 (no 403, para no confirmar que existe).
3. **Dado:** un técnico. **Cuando:** llama a una ruta de administración. **Entonces:** recibe 403.
4. **Dado:** la matriz de `docs/domain/roles-permisos.md`. **Cuando:** se ejecutan los tests. **Entonces:** hay un test de acceso permitido y uno denegado por cada ruta.
5. **Dado:** una ruta nueva sin rol declarado. **Cuando:** corre CI. **Entonces:** el test de rutas falla.

## Notas técnicas

- Rutas del técnico bajo `/tech/`, de administración bajo `/admin/`. Ver ADR 0006.

## Notas de implementación

- `app/api/deps.py`: `get_current_user` (decodifica el JWT, carga el usuario; 401 si falta, es inválido o está inactivo) y `require_role(*roles)`, la dependencia común que exige rol y responde 403 si no corresponde (criterio 1). La dependencia lleva un atributo `required_roles` que usa el test de contrato.
- Ruta real protegida: `GET /auth/me` (cualquier rol autenticado) devuelve el usuario actual.
- Test de contrato de rutas (`test_route_authorization.py`, criterio 5): recorre todas las rutas (incluyendo los routers incluidos de FastAPI 0.143) y falla si alguna no pública no declara rol. Verificado que se pone en rojo al agregar una ruta sin `require_role`. La lista de rutas públicas (salud, login, docs) está en un solo lugar.
- Acceso permitido y denegado por ruta (criterios 3 y 4): se prueba el `require_role` real con un app de test que monta rutas `/admin/` y `/tech/` (rol correcto 200, rol incorrecto 403), más `/auth/me` (con token 200, sin token o inactivo 401).
- Criterio 2 (un recurso que no es del técnico responde 404, no 403): es la convención de ADR 0006 y de `roles-permisos.md` (regla 2). Se demuestra el patrón con una ruta de test que chequea pertenencia y responde 404; se aplica de verdad cuando existan los endpoints de órdenes (E05).
