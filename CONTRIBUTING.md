# Cómo contribuir

Este documento es la fuente de verdad del workflow. Los agentes de IA lo siguen igual que las personas.

## Flujo de trabajo

```
Historia (docs/stories) -> Issue -> Rama desde develop -> PR -> CI + revisión -> Squash merge a develop
  -> ambiente develop (se prueba) -> PR develop -> main (merge commit) -> Producción
```

### 1. Historias primero

- Todo cambio de comportamiento parte de una historia en `docs/stories/<epica>/`.
- Una historia tiene que estar en estado `ready` para implementarse (ver [docs/stories/README.md](docs/stories/README.md)).
- Si aparece trabajo nuevo, primero se escribe la historia (comando `/new-story` si usás Claude Code) y recién después el código.
- Las historias bloqueadas por una decisión pendiente (`blocked_by`) no se implementan hasta cerrar la decisión.

### 2. Ramas

Dos ramas largas, las dos protegidas (PR obligatorio y `ci-ok` en verde; ADR 0011):

- **`develop`**: la rama por defecto. Todo el trabajo sale de acá y vuelve acá por PR. Cada merge se publica solo en el ambiente develop.
- **`main`**: lo que está en producción. Solo recibe publicaciones desde `develop` y arreglos urgentes.

Las ramas de trabajo viven poco.

| Prefijo | Uso | Ejemplo |
|---|---|---|
| `feat/` | Historia nueva | `feat/E04-03-asignar-orden` |
| `fix/` | Corrección de bug | `fix/E05-02-firma-sin-dni` |
| `docs/` | Solo documentación o historias | `docs/E07-ajuste-checklist` |
| `chore/` | Mantenimiento, dependencias, CI | `chore/actualizar-ruff` |

Regla: el ID de la historia va al principio del nombre de la rama cuando existe.

### 3. Commits

[Conventional Commits](https://www.conventionalcommits.org/es/) con scope opcional del área:

```
feat(backend): asignar orden a un técnico (E04-03)
fix(pwa): no perder la firma al rotar el celular (E05-02)
docs(stories): agregar criterios a E07-04
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`.

### 4. Pull requests

- Un PR por historia, lo más chico posible. Si pasa de unas 400 líneas de código, partirlo.
- Completar la plantilla: historia, qué cambia, cómo se probó, checklist de la Definición de Terminado.
- Base del PR: `develop`. Título en formato Conventional Commits. Se hace **squash merge**, así que el título queda como mensaje en `develop`.
- CI en verde (check `ci-ok`) y revisión de Claude resuelta o descartada con justificación.
- Cambios en `docs/stories/` y `docs/domain/` los revisa el analista de negocio (ver `.github/CODEOWNERS`).

### 5. Definición de Terminado

Ver [docs/workflow/definition-of-done.md](docs/workflow/definition-of-done.md). Resumen: criterios de aceptación cumplidos y probados, migraciones reversibles, sin precios en respuestas del técnico, documentación actualizada, sin secretos ni datos reales.

### 6. Entornos y releases

| Entorno | Qué despliega | Cuándo |
|---|---|---|
| Local | Docker Compose | siempre |
| Develop | `develop` | automático en cada merge, con datos ficticios |
| Producción | `main` | automático en cada merge (la publicación por tag con aprobación queda para E00-06) |

- **Publicar en producción:** PR de `develop` a `main`, titulado `chore(release): <resumen>`, con **merge commit** (no squash), para que las dos ramas compartan la historia.
- **Arreglo urgente de producción:** rama `fix/...` desde `main`, PR a `main` (squash) y, en cuanto entra, un PR de `main` a `develop` (merge commit) para no perderlo.

Hosting en la historia E00-05 y en [ADR 0004](docs/architecture/adr/0004-hosting-paas-postgres-administrado.md); el ambiente develop en [ADR 0011](docs/architecture/adr/0011-ambiente-develop.md) y en [docs/workflow/despliegue.md](docs/workflow/despliegue.md#ambiente-develop).

## Reglas de código

- **Backend**: Python 3.12, tipado, `ruff` (lint y formato) y `mypy`. Capas en `backend/README.md`.
- **Frontend**: TypeScript estricto, ESLint y Prettier. Estado del servidor con TanStack Query.
- **Base de datos**: toda modificación va por migración Alembic, reversible y revisable. Nada de cambios manuales.
- **Tests**: cada criterio de aceptación tiene al menos un test. Los tests de permisos y de "el técnico no ve precios" son obligatorios.
- **Español** en dominio, historias, textos de UI y documentación. **Inglés** en nombres de código (clases, funciones, tablas, columnas).

## Reglas de dominio que no se negocian

1. Borrado lógico (`deleted_at`). Nunca se borra físicamente.
2. El técnico nunca ve precios, mano de obra ni historial de clientes. Se garantiza en la API, no en la interfaz.
3. Fechas de negocio y precios viven en tablas de transacción, no en la entidad padre.
4. El precio de un repuesto se estampa en el momento en que se usa.
5. Las fotos van a almacenamiento de objetos, nunca dentro de la base.
6. Los catálogos se editan por la app. Cada valor repetido en "Otro" se puede promover a la lista.

## Seguridad

Este repositorio es público. Leer [SECURITY.md](SECURITY.md) antes del primer commit.
