---
id: E01-08
title: "Reactivar un usuario dado de baja"
epic: E01
phase: 1
priority: should
status: done
roles: [admin, owner]
size: S
areas: [backend, web-admin]
depends_on: [E01-03]
blocked_by: []
assumes: []
---

# E01-08 Reactivar un usuario dado de baja

## Historia

**Como** administración, **quiero** ver a los usuarios dados de baja y poder reactivarlos, **para** deshacer una baja por error o recuperar a alguien que vuelve sin crearle otra cuenta.

## Criterios de aceptación

1. **Dado:** usuarios dados de baja. **Cuando:** administración entra a Usuarios. **Entonces:** los ve en una lista aparte, con su rol y la fecha de baja; no aparecen entre los activos.
2. **Dado:** un usuario dado de baja. **Cuando:** administración lo reactiva. **Entonces:** vuelve a la lista de activos con el mismo rol, conserva su historial y puede iniciar sesión con la contraseña que tenía.
3. **Dado:** un técnico. **Cuando:** intenta ver o reactivar dados de baja. **Entonces:** el sistema lo rechaza.

## Notas técnicas

- La baja es borrado lógico (E01-03): reactivar es limpiar `deleted_at` y volver `is_active=true`. El correo sigue siendo único, así que no hay choque al reactivar.
- Si no recuerda la contraseña, se restablece aparte (E01-05).

## Hecho

- `GET /admin/users/deactivated` lista los dados de baja por nombre, con `deleted_at`; `POST /admin/users/{id}/reactivate` deshace la baja (sobre un usuario activo no cambia nada; uno inexistente da 404). Los dos con `require_role(admin, owner)`.
- web-admin: sección "Dados de baja" debajo de la lista de Usuarios, con la fecha de baja y el botón "Reactivar". Dar de baja o reactivar recarga las dos listas.
