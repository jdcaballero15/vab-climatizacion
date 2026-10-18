---
id: E01-03
title: "Gestionar usuarios"
epic: E01
phase: 1
priority: must
status: done
roles: [admin, owner]
size: M
areas: [backend, web-admin]
depends_on: [E01-04]
blocked_by: []
assumes: []
---

# E01-03 Gestionar usuarios

## Historia

**Como** administración, **quiero** crear, editar y dar de baja usuarios y asignarles un rol, **para** controlar quién usa el sistema.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un usuario con nombre, correo y rol. **Entonces:** el usuario puede iniciar sesión con una contraseña inicial.
2. **Dado:** un correo ya registrado. **Cuando:** intento crear otro usuario con el mismo. **Entonces:** se rechaza con un mensaje claro.
3. **Dado:** un usuario. **Cuando:** se lo da de baja. **Entonces:** queda inactivo (borrado lógico), conserva su historial y no puede iniciar sesión.
4. **Dado:** un técnico con órdenes asignadas abiertas. **Cuando:** se lo da de baja. **Entonces:** el sistema avisa y pide reasignarlas.
5. **Dado:** un usuario con rol técnico. **Cuando:** intenta acceder a esta pantalla o a su API. **Entonces:** recibe acceso denegado.

## Preguntas abiertas

- ¿Pueden las dos personas de administración gestionar usuarios, o solo dirección?
  - Resuelto según la matriz de `roles-permisos.md`: administración y dirección (`admin` y `owner`) gestionan usuarios; el técnico no. Si el negocio prefiere restringirlo a dirección, se cambia la lista de roles de `require_role`.

## Notas de implementación

- Backend: endpoints `/admin/users` (crear, listar, ver, editar, dar de baja), todos con `require_role(admin, owner)`. El servicio `services/users.py` concentra la lógica; el repositorio filtra `deleted_at`.
  - Criterio 1: crear usuario con nombre, correo, rol y contraseña inicial (hasheada con Argon2); el usuario puede iniciar sesión enseguida.
  - Criterio 2: correo duplicado (incluso de un usuario dado de baja, por la unicidad en la base) devuelve 409 con `code: email_already_exists`.
  - Criterio 3: dar de baja es borrado lógico (`deleted_at` + `is_active=false`): conserva la fila y su historial, y bloquea el login.
  - Criterio 5: el técnico recibe 403 en estos endpoints (cubierto por el test y por el contrato de rutas de E01-04).
- Frontend (web-admin): pantalla de usuarios (lista, alta con selección de rol, baja) visible solo para admin y dirección, con el cliente tipado y el token de sesión en el header.
- **Criterio 4** (avisar y pedir reasignación si el técnico tiene órdenes abiertas): queda pendiente para cuando existan las órdenes (E04); hoy no hay órdenes que chequear. La baja ya es reversible por ser borrado lógico.
