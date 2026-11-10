---
id: E01-06
title: "Bloqueo temporal por intentos fallidos"
epic: E01
phase: 1
priority: should
status: done
roles: [admin, technician, owner]
size: S
areas: [backend]
depends_on: [E01-01]
blocked_by: []
assumes: []
---

# E01-06 Bloqueo temporal por intentos fallidos

## Historia

**Como** dirección, **quiero** que el sistema frene los intentos repetidos de adivinar contraseñas, **para** proteger las cuentas.

## Criterios de aceptación

1. **Dado:** un usuario. **Cuando:** falla 5 veces seguidas en 10 minutos. **Entonces:** se bloquea el inicio de sesión de esa cuenta durante 15 minutos.
2. **Dado:** un bloqueo. **Cuando:** ocurre. **Entonces:** el usuario ve un mensaje claro con el tiempo de espera y queda registrado.
3. **Dado:** un bloqueo activo. **Cuando:** administración lo revisa. **Entonces:** puede levantarlo manualmente.

## Notas técnicas

- Umbrales configurables. Aplicar también un límite por dirección IP.

## Hecho

- Tabla `login_failure` (correo en minúsculas, IP, fecha). Con 5 fallos en 10 minutos la cuenta queda bloqueada 15 minutos; desde una misma IP, el tope es 20 en 10 minutos. Umbrales en la configuración (`LOGIN_*`).
- Bloqueada, el login responde 429 `account_locked` con los minutos que faltan; web-admin y PWA muestran ese mensaje. Un correo que no existe también suma fallos (no revela si la cuenta existe). El bloqueo queda en el log con el id del usuario, sin el correo.
- `GET /admin/users` trae `locked_until`; `POST /admin/users/{id}/unlock` lo levanta. web-admin: "Bloqueado hasta las HH:MM" y "Desbloquear" en Usuarios. Entrar bien borra (borrado lógico) los fallos.
