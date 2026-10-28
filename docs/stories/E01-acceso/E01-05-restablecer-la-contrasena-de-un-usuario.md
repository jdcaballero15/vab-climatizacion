---
id: E01-05
title: "Restablecer la contraseña de un usuario"
epic: E01
phase: 1
priority: should
status: in_progress
roles: [admin, technician, owner]
size: M
areas: [backend, web-admin, pwa]
depends_on: [E01-03, E01-07]
blocked_by: []
assumes: []
---

# E01-05 Restablecer la contraseña de un usuario

## Historia

**Como** administración, **quiero** restablecer la contraseña de un usuario que la olvidó, **para** que una escuadrilla no quede sin trabajar por un olvido.

## Criterios de aceptación

1. **Dado:** administración en la pantalla de Usuarios. **Cuando:** restablece la contraseña de un usuario (con confirmación). **Entonces:** se genera una contraseña temporal que se muestra una sola vez, con botón para copiarla; después no se puede volver a ver.
2. **Dado:** un restablecimiento. **Cuando:** se realiza. **Entonces:** se cierran todas las sesiones abiertas de ese usuario (sus refresh tokens quedan revocados).
3. **Dado:** un usuario con contraseña temporal. **Cuando:** inicia sesión (en la administración o en el celular). **Entonces:** ve la pantalla para elegir una contraseña nueva antes de seguir, y la API le niega todo lo demás (403, `password_change_required`) hasta que la cambie.
4. **Dado:** la pantalla de cambio. **Cuando:** la nueva contraseña tiene menos de 8 caracteres, es igual a la temporal o no coincide con la repetición. **Entonces:** se avisa y no se guarda.
5. **Dado:** un restablecimiento. **Cuando:** se realiza. **Entonces:** queda registrado quién lo hizo, sobre quién y cuándo; la contraseña nunca queda en logs ni en la base en claro.
6. **Dado:** un técnico. **Cuando:** intenta restablecer una contraseña. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Recuperar la contraseña por correo por cuenta propia (necesita mail transaccional, E00-10, bloqueada por `D-009`).
- Que cada usuario cambie su contraseña cuando quiera desde su perfil (el endpoint de cambio queda, pero sin pantalla propia fuera del caso temporal).
- Política de contraseñas más estricta o vencimiento.

## Notas técnicas

- `POST /admin/users/{id}/password-reset` (admin y dueño): genera la temporal con `secrets` (12 caracteres legibles, sin 0/O ni 1/l), guarda el hash, marca `must_change_password`, revoca refresh tokens y responde la temporal una única vez.
- Columnas nuevas en `app_user`: `must_change_password` (bool), `password_reset_at`, `password_reset_by`. No hay tabla de auditoría todavía: esto cubre el criterio 5 con el último restablecimiento; el historial completo llega con la auditoría general. Migración reversible.
- `POST /auth/password` (cualquier rol autenticado): contraseña actual y nueva; limpia `must_change_password`.
- `require_role` niega con 403 `password_change_required` si el usuario tiene `must_change_password`, salvo `/auth/me`, `/auth/password`, `/auth/refresh` y `/auth/logout`. `UserOut` suma `must_change_password` para que los clientes muestren la pantalla al entrar o al recargar.
- La pantalla de cambio es igual en web-admin y en la PWA (cada app la suya, como el resto del acceso).

## Notas de implementación

- Se entrega en tres PR: backend (este), web-admin (botón en Usuarios y pantalla de cambio) y pwa-tecnico (pantalla de cambio).
- **Backend (hecho):** migración `c5e9a3d7b214` (`must_change_password`, `password_reset_at`, `password_reset_by` en `app_user`). `POST /admin/users/{id}/password-reset` responde `{temporary_password}` con `Cache-Control: no-store`, revoca todos los refresh tokens del usuario y guarda solo el hash. `require_role` niega con 403 `password_change_required` mientras la marca esté puesta, salvo en las rutas declaradas con `allow_temporary_password=True` (`/auth/me` y `/auth/password`); refresh y logout no usan rol y siguen andando. `POST /auth/password` (`current_password`, `new_password` de 8 a 128) responde el `UserOut`; 422 `invalid_current_password` o `password_unchanged`. `UserOut` y `UserAdminOut` suman `must_change_password`. La repetición de la contraseña nueva se valida solo en los clientes.
