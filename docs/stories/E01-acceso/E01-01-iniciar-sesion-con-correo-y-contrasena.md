---
id: E01-01
title: "Iniciar sesión con correo y contraseña"
epic: E01
phase: 1
priority: must
status: done
roles: [admin, technician, owner]
size: S
areas: [backend, web-admin, pwa]
depends_on: [E00-01]
blocked_by: []
assumes: [D-007]
---

# E01-01 Iniciar sesión con correo y contraseña

## Historia

**Como** usuario del sistema, **quiero** iniciar sesión con mi correo y contraseña, **para** acceder solo a lo que corresponde a mi rol.

## Criterios de aceptación

1. **Dado:** un usuario activo con credenciales correctas. **Cuando:** inicia sesión. **Entonces:** recibe una sesión y ve la pantalla de inicio de su rol.
2. **Dado:** credenciales incorrectas. **Cuando:** intenta iniciar sesión. **Entonces:** ve un mensaje genérico que no revela si el correo existe.
3. **Dado:** un usuario dado de baja. **Cuando:** intenta iniciar sesión. **Entonces:** se le rechaza.
4. **Dado:** una contraseña. **Cuando:** se guarda. **Entonces:** se almacena con Argon2 y nunca en texto plano ni en logs.

## Notas técnicas

- Sesión con JWT de corta duración y token de refresco rotativo. Ver E01-02.

## Notas de implementación

- Promovida de `draft` a `done` sobre la propuesta vigente de **D-007** (correo + contraseña, JWT). Si el negocio define otro método (cuenta Microsoft/Google), se retoca.
- Backend:
  - Tabla `app_user` (modelo `User`, enum `user_role`) con su migración Alembic reversible (el enum se elimina a mano en el `downgrade`).
  - Contraseñas con **Argon2** (`argon2-cffi`); nunca en texto plano ni en logs (criterio 4).
  - `POST /auth/login`: valida credenciales y devuelve `{access_token, token_type, user}` con un JWT corto (`PyJWT`). Credenciales incorrectas, correo inexistente y usuario inactivo devuelven el mismo 401 genérico, con tiempo constante, para no revelar si el correo existe (criterios 2 y 3).
  - Capas respetadas: `services/auth.py` (caso de uso), `db/repositories/user.py` (filtra `deleted_at`), `api/auth.py` (ruta). El token de refresco y el cierre de sesión son E01-02.
- Frontend (web-admin y pwa-tecnico): la pantalla de login llama al endpoint con el cliente tipado generado, muestra el mensaje genérico ante un error y, al entrar, lleva a una pantalla de inicio que saluda según el rol (criterio 1). La sesión se mantiene en memoria; persistirla y refrescarla es E01-02.
- El `APP_SECRET_KEY` debe tener 32+ bytes en entornos reales (ver `.env.example`).
- Nuevas dependencias (justificadas): `argon2-cffi`, `pyjwt`, `email-validator`.
