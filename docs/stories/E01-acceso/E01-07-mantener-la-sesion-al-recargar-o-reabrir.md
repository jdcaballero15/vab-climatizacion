---
id: E01-07
title: "Mantener la sesión al recargar o reabrir"
epic: E01
phase: 1
priority: must
status: ready
roles: [admin, technician, owner]
size: M
areas: [backend, web-admin, pwa]
depends_on: [E01-02]
blocked_by: []
assumes: []
---

# E01-07 Mantener la sesión al recargar o reabrir

## Historia

**Como** usuario del sistema (en la oficina o con el celular de la escuadrilla), **quiero** seguir adentro si recargo la página o vuelvo a abrir la app, **para** no escribir la contraseña cada vez.

Decisión técnica en el [ADR 0010](../../architecture/adr/0010-sesion-persistente-con-cookie.md): refresh token en una cookie `httpOnly` y la API en `/api` de cada sitio.

## Criterios de aceptación

1. **Dado:** un usuario que ingresó. **Cuando:** recarga la página o cierra y vuelve a abrir la app. **Entonces:** entra directo, sin ver el login.
2. **Dado:** un usuario que ingresó. **Cuando:** pasan más de 30 días sin usarla, o el refresh token ya se usó, o no hay cookie. **Entonces:** ve el login.
3. **Dado:** un usuario que ingresó. **Cuando:** cierra sesión y recarga. **Entonces:** ve el login; el token quedó revocado en el servidor y la cookie borrada.
4. **Dado:** un usuario que la administración dio de baja. **Cuando:** abre la app con la cookie que tenía. **Entonces:** ve el login (E01-02, criterio 4).
5. **Dado:** cualquier script de la página. **Cuando:** intenta leer el refresh token. **Entonces:** no puede: no está en ninguna respuesta de la API ni en el almacenamiento del navegador, solo en la cookie `httpOnly`.
6. **Dado:** una página de otro sitio. **Cuando:** llama a la API de sesión. **Entonces:** la cookie no viaja (`SameSite=Strict`) y no obtiene una sesión.

## Fuera de alcance

- "Recordarme" opcional o duración distinta por rol.
- Ver o cerrar las sesiones abiertas de un usuario desde la administración.

## Notas técnicas

- **Backend:** login y refresh agregan `Set-Cookie` con `HttpOnly`, `Secure`, `SameSite=Strict`, `Path` configurable (`/api/auth` en los sitios desplegados) y `Max-Age` igual a `refresh_token_expire_days`. `/auth/refresh` y `/auth/logout` aceptan el token de la cookie o del cuerpo (el cuerpo pasa a ser opcional). La respuesta de `/auth/refresh` suma `user`, para que el cliente no tenga que pedir `/auth/me` al abrir. `/auth/logout` borra la cookie aunque el token ya no sea válido.
- **Clientes:** `VITE_API_URL=/api`. Al arrancar, `POST /auth/refresh` sin cuerpo (con `credentials: "include"`); mientras tanto se muestra "Cargando". El refresh token deja de guardarse en memoria. El interceptor de 401 renueva siempre con la cookie.
- **Render:** en cada sitio, regla `rewrite` de `/api/*` a `https://vab-ot-api.onrender.com/*`, antes de la regla de `index.html`. Hay que confirmar al desplegar que deja pasar POST y `Set-Cookie`; si no, plan B del ADR 0010.
- **Local:** `server.proxy` de Vite reenvía `/api` a `http://localhost:8000` sacando el prefijo.
- Se entrega en cuatro PR: backend (cookie, cuerpo todavía compatible), pwa-tecnico (con su regla en `render.yaml`), web-admin (ídem) y backend otra vez para sacar `refresh_token` de las respuestas y de los cuerpos (criterio 5).
