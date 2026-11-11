---
id: E12-02
title: "Borrado lógico y restauración"
epic: E12
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E12-02 Borrado lógico y restauración

## Historia

**Como** administración, **quiero** que nada se borre de verdad y poder restaurar lo dado de baja, **para** recuperar errores sin perder historial.

## Criterios de aceptación

1. **Dado:** una baja de cualquier entidad. **Cuando:** se realiza. **Entonces:** se completa `deleted_at` y no se ejecuta ningún `DELETE`.
2. **Dado:** las consultas comunes. **Cuando:** se ejecutan. **Entonces:** excluyen los registros dados de baja.
3. **Dado:** un test de arquitectura. **Cuando:** recorre el código. **Entonces:** falla si encuentra `DELETE` físico sobre tablas de negocio.
4. **Dado:** un registro dado de baja. **Cuando:** administración lo restaura. **Entonces:** vuelve a estar disponible y queda auditado.

## Decisiones (Gonza, 2026-11-10)

- Nada nuevo: todo repositorio ya filtraba `deleted_at IS NULL` (`BaseRepository`).

## Hecho

- Test de arquitectura `tests/test_soft_delete_architecture.py`: falla si el código de `app/` tiene `session.delete(...)`, `delete(Modelo)` o `DELETE FROM`.
- Restauración con auditoría para clientes y equipos (E03-07), en `audit_event`.
