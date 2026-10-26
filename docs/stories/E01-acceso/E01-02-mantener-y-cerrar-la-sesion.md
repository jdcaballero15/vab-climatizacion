---
id: E01-02
title: "Mantener y cerrar la sesión"
epic: E01
phase: 1
priority: must
status: in_progress
roles: [admin, technician, owner]
size: S
areas: [backend, web-admin, pwa]
depends_on: [E01-01]
blocked_by: []
assumes: []
---

# E01-02 Mantener y cerrar la sesión

## Historia

**Como** usuario del sistema, **quiero** que mi sesión se mantenga mientras trabajo y poder cerrarla, **para** no tener que volver a ingresar a cada rato y proteger el equipo si lo pierdo.

## Criterios de aceptación

1. **Dado:** una sesión vigente. **Cuando:** vence el token de acceso. **Entonces:** se renueva en segundo plano sin interrumpirme.
2. **Dado:** un usuario. **Cuando:** elige cerrar sesión. **Entonces:** el token de refresco se invalida y se limpian los datos locales.
3. **Dado:** un técnico en el celular. **Cuando:** cierra sesión. **Entonces:** se borran las órdenes guardadas en el dispositivo (si hay datos offline, avisa antes si hay cambios sin sincronizar).
4. **Dado:** un administrador. **Cuando:** da de baja a un usuario. **Entonces:** sus sesiones activas dejan de funcionar.

## Notas técnicas

- El refresh token se guarda en memoria (mismo criterio que el access token de E01-03): la sesión se mantiene mientras la pestaña o la app siguen abiertas; persistirla entre recargas quedaría para una decisión aparte (riesgo XSS en un repo público).

## Notas de implementación

- Se entrega en dos partes. Esta historia queda `in_progress` hasta completar la PWA.
- **Backend (hecho):**
  - Modelo `refresh_token` con migración Alembic reversible. Solo se guarda el hash (SHA256), nunca el token en claro.
  - `POST /auth/refresh` **rota** el token: revoca el presentado y emite un access token y un refresh token nuevos. Un usuario inactivo no puede refrescar (criterio 4).
  - `POST /auth/logout` invalida el refresh token (204, idempotente). El login (E01-01) ahora emite también un refresh token.
- **web-admin (hecho):**
  - El token store (`features/auth/token.ts`) guarda también el refresh token en memoria.
  - Interceptor en `api/client.ts`: ante un 401 renueva el token con `/auth/refresh` y reintenta la request original de forma transparente, con un único refresh en vuelo compartido entre requests concurrentes (criterio 1). Si la renovación falla (refresh vencido o usuario dado de baja), limpia los tokens y emite un aviso de sesión caída que devuelve al login (criterio 4).
  - `features/auth/useLogout.ts`: llama a `/auth/logout` y, pase lo que pase con esa llamada, limpia los tokens en memoria y la cache de TanStack Query (criterio 2).
  - Limitación conocida: un reintento tras 401 no puede reenviar el cuerpo de una request que ya lo consumió (p. ej. un POST); en ese caso se devuelve el 401 y el token queda renovado para la próxima acción.
  - Se regeneró `openapi.json` y `src/api/schema.d.ts` desde el backend para incorporar `/auth/refresh`, `/auth/logout` y `refresh_token`.
- **pwa-tecnico (pendiente, otra PR):** hoy no tiene token store ni interceptor; hay que replicar el cableo de web-admin.
- **Criterio 3 (técnico offline):** diferido. El almacenamiento offline está bloqueado por **D-001**; hasta que exista no hay órdenes guardadas que borrar ni cambios sin sincronizar que avisar al cerrar sesión.
