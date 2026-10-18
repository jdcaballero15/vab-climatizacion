---
id: E00-01
title: "Base del backend con PostgreSQL y migraciones"
epic: E00
phase: 1
priority: must
status: done
roles: [dev]
size: S
areas: [backend, infra]
depends_on: []
blocked_by: []
assumes: []
---

# E00-01 Base del backend con PostgreSQL y migraciones

## Historia

**Como** equipo de desarrollo, **quiero** un backend con conexión asíncrona a PostgreSQL y Alembic configurados, **para** construir los módulos sobre una base común.

## Criterios de aceptación

1. **Dado:** el entorno local levantado con `make up`. **Cuando:** consulto `GET /health/ready`. **Entonces:** la respuesta indica que la base responde.
2. **Dado:** una base vacía. **Cuando:** corro `alembic upgrade head`. **Entonces:** se crea el esquema inicial sin errores y `alembic downgrade base` lo deshace.
3. **Dado:** el modelo base. **Cuando:** se crea cualquier tabla. **Entonces:** incluye `id` (uuid), `created_at`, `updated_at` y `deleted_at`.
4. **Dado:** un repositorio base. **Cuando:** consulto registros. **Entonces:** excluye por defecto los que tienen `deleted_at`.

## Notas técnicas

- Capas y convenciones en `backend/README.md`. El repositorio base es el único lugar que filtra `deleted_at`.
- En CI las pruebas usan el servicio Postgres del workflow.

## Notas de implementación

- Capa de base de datos en `app/db/`: `base.py` (`Base` declarativa y `TimestampedBase` con `id` uuid, `created_at`, `updated_at`, `deleted_at`), `session.py` (engine async, `async_sessionmaker` y la dependencia `get_session`) y `repository.py` (`BaseRepository` genérico que filtra `deleted_at IS NULL` salvo `include_deleted=True`).
- `GET /health/ready` hace `SELECT 1`: responde `{"status":"ready","database":"ok"}` con 200 si la base responde y 503 (`not_ready`) si no.
- Alembic async configurado en `backend/alembic.ini` y `backend/migrations/`. La migración `0001_initial` es la línea base sin tablas de dominio (las agregan las historias siguientes); `upgrade head` y `downgrade base` verificados por CLI y por test.
- Tests contra Postgres real (uno por criterio) en `backend/tests/`. `conftest.py` apunta a la base `ot_test` vía `DATABASE_URL` y dispone el engine por test.
