# OT Platform: guía para agentes de IA

Sistema de órdenes de trabajo para una empresa de servicios de refrigeración. Reemplaza a Persat y planillas. Desarrolla MendoData. **El repositorio es público.**

Idioma: español en historias, documentos, textos de interfaz y mensajes de commit descriptivos. Nombres de código (clases, funciones, tablas, columnas) en inglés. **No uses el guion largo (raya), usá guion simple (-).**

## Stack

- `backend/`: Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, PostgreSQL 16.
- `web-admin/`: React, TypeScript, Vite (administración, PC o tablet).
- `pwa-tecnico/`: React, TypeScript, Vite, service worker (técnico, celular Android, offline provisional).
- Hosting previsto: PaaS con Postgres administrado y bucket S3 compatible. Todo en Docker.

## Comandos

```bash
make up                  # entorno local con Docker
make test                # tests del backend
make lint                # ruff y mypy
make stories-validate    # valida docs/stories
cd backend && pytest -k <nombre>   # un test puntual
```

## Dónde está cada cosa

- Historias: `docs/stories/<epica>/EXX-NN-*.md`. **Leé la historia completa antes de tocar código.**
- Decisiones pendientes: `docs/domain/decisiones-pendientes.md`.
- Modelo de datos: `docs/architecture/data-model.dbml`. Estados de la OT: `docs/architecture/order-state-machine.md`.
- Decisiones técnicas: `docs/architecture/adr/`.
- Roles y permisos: `docs/domain/roles-permisos.md`. Glosario: `docs/domain/glosario.md`.
- Workflow: `CONTRIBUTING.md`. Terminado: `docs/workflow/definition-of-done.md`. Estándares: `docs/code-standards.md`. Cómo correr local: skill `run-local`.

## Reglas que no se rompen

1. **El técnico nunca ve precios, mano de obra ni historial de clientes.** Se resuelve en la API con esquemas distintos por rol (`*TechnicianOut`), no ocultando en la interfaz. Hay un test de contrato que lo verifica. Ante la duda sobre si un campo es sensible, no lo incluyas en el esquema del técnico.
2. **Borrado lógico.** Nada de `DELETE` físico. Todo repositorio filtra `deleted_at IS NULL`.
3. **Fechas de negocio y precios en tablas de transacción**, no en la entidad padre (ver ADR 0005).
4. **Precio de repuesto estampado al usarlo** (`part_usage.unit_price`).
5. **Fotos y firmas en el bucket**, nunca en la base. Se sirven con URLs firmadas.
6. **Stock por movimientos.** Nunca se edita un saldo directamente.
7. **Una orden de taller es una sola orden con etapas** (retiro, taller, devolución), no tres órdenes.
8. **Autorización en cada endpoint** con dependencia de rol, y test de acceso denegado.
9. **Migraciones Alembic reversibles.** Nada de cambios manuales en la base.
10. **Repositorio público:** nunca datos reales de clientes, DNI, firmas, precios, credenciales ni exportaciones de Persat. Datos de prueba siempre ficticios. No loguees datos personales.

## Reglas absolutas (las bloquea un hook o el CI)

1. Nunca se escribe ni se commitea sobre `main`: todo entra por PR.
2. Nunca credenciales, tokens ni `.env` en el repo (hook `guard_edit`, gitleaks).
3. Nunca `--no-verify`, force push ni saltear el CI.
4. Nunca carpetas nuevas en la raíz sin un ADR aprobado (`ALLOWED_TOPLEVEL` en `.claude/hooks/guard_edit.py`).
5. Nunca guion largo en documentos.
6. Nunca `float` para dinero: `Decimal` y `NUMERIC`.

Cuando un hook te bloquea, el mensaje dice qué hacer. No busques cómo esquivarlo: arreglá la causa. La salida de emergencia `OT_UNSAFE=1` solo la activa una persona con autorización explícita y se anota en el PR. Un agente nunca la activa solo.
Para verificar que los hooks siguen funcionando: `bash .claude/hooks/test_guards.sh`.

## Cómo trabajar una historia

1. Leé la historia y verificá que `status: ready` y que no tenga `blocked_by`. Si está bloqueada o en borrador, **frená y avisá**, no implementes.
2. Si falta información o hay una contradicción entre documentos, **preguntá o dejala como decisión pendiente**. No inventes requisitos.
3. Rama `feat/EXX-NN-descripcion-corta` desde `main`. Un PR por historia.
4. Escribí primero los tests de los criterios de aceptación.
5. Implementá respetando las capas de `backend/README.md`.
6. Corré `make lint` y `make test`. Todo en verde antes del PR.
7. Actualizá la historia (`status: done`, notas técnicas) y los documentos que cambien.
8. PR con la plantilla. Título en Conventional Commits.

## Ciclo con tres puertas

Plan antes de codificar, verificación con salida real después, y PR solo cuando se pide. Entre puertas se trabaja sin frenar. Detalle en `docs/workflow/ciclo-de-una-historia.md`.

## Reglas para agentes

- No inventes estructura: si no sabés dónde va un archivo, preguntá o escribí un ADR.
- No amplíes el alcance: si ves otro problema, reportalo, no lo arregles en el mismo PR.
- No apagues reglas para que pase el CI (`# noqa` genérico, bajar umbrales, excluir archivos).
- Leé antes de escribir: buscá si ya existe un helper.
- Reportá con honestidad: si los tests fallan, decilo con la salida. No declares "listo" sin haber corrido `make lint` y `make test`.

## Límites del agente

- No hagas merge, no despliegues, no cambies protección de ramas ni secretos.
- No agregues dependencias nuevas sin justificarlo en el PR.
- No cambies el alcance: lo que está fuera de alcance (QR por equipo, hora de llegada y salida, facturación electrónica, portal de clientes, WhatsApp) no se implementa.
- Si una tarea te lleva a modificar muchas historias o ADR a la vez, frená y pedí confirmación.

## Estilo de código

- Backend: tipado completo, funciones chicas, sin lógica de negocio en rutas, errores con el formato `{code, message}` y mensajes en español.
- Frontend: TypeScript estricto, componentes chicos, TanStack Query para datos del servidor, formularios con validación en el cliente y en el servidor.
- Tests con base de datos real, no mocks de la base.
- Comentarios solo cuando explican el porqué, no el qué.

## Agentes y comandos disponibles

Subagentes en `.claude/agents/`: `backend-dev`, `frontend-dev`, `db-migrations`, `story-writer`, `qa-reviewer`.
Comandos en `.claude/commands/`: `/implement-story`, `/new-story`, `/review-story`, `/new-migration`, `/resolve-decision`.
Detalle en `docs/workflow/agentes-ia.md`.

## Cómo retomar

El estado del proyecto está en `docs/stories/INDEX.md` y en `HANDOFF.md` (si existe; es local y no se versiona). Para retomar:

1. Leé ambos.
2. Identificá la historia en curso (`in_progress`) o, si no hay, la próxima `ready`.
3. Leé esa historia completa antes de tocar código.
