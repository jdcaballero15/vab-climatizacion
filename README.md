# OT Platform

Sistema de órdenes de trabajo (OT) para empresas de servicios de refrigeración. Reemplaza a Persat y a las planillas dispersas con un sistema propio que cubre el circuito completo: pedido, asignación, ejecución en campo, revisión, facturación y cobro.

Desarrollado por [MendoData](https://github.com/MendoData).

> Este repositorio es público. No se suben datos reales de clientes, precios, DNI, firmas, credenciales ni exportaciones de Persat. Ver [SECURITY.md](SECURITY.md).

## Qué hace

- **App de administración** (PC o tablet): alta y asignación de órdenes, revisión, facturado y cobrado, fichas de cliente y equipo, catálogos, stock, tablero.
- **App del técnico** (PWA para celular Android): órdenes asignadas, cierre con opciones predefinidas, materiales sin precios, foto, observación y firma del cliente. El técnico nunca ve precios, mano de obra ni historial de clientes.
- **Automatizaciones**: mantenimiento preventivo mensual, comprobantes PDF, informe mensual por mail.

## Estructura del monorepo

```
backend/        API en Python (FastAPI) + PostgreSQL
web-admin/      App de administración (React + TypeScript)
pwa-tecnico/    App del técnico (React + TypeScript, PWA, con conexión)
docs/           Arquitectura, dominio, workflow e historias de usuario
scripts/        Utilidades (validar y sincronizar historias, bootstrap de GitHub)
.github/        CI, plantillas, automatizaciones con IA
.claude/        Agentes, comandos y permisos para Claude Code
```

## Documentación

| Qué buscás | Dónde |
|---|---|
| Visión general de la arquitectura | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Decisiones técnicas (ADR) | [docs/architecture/adr/](docs/architecture/adr/) |
| Modelo de datos | [docs/architecture/data-model.dbml](docs/architecture/data-model.dbml) |
| Máquina de estados de la OT | [docs/architecture/order-state-machine.md](docs/architecture/order-state-machine.md) |
| Glosario, roles y permisos | [docs/domain/](docs/domain/) |
| Decisiones pendientes | [docs/domain/decisiones-pendientes.md](docs/domain/decisiones-pendientes.md) |
| Historias de usuario | [docs/stories/](docs/stories/README.md) |
| Cómo trabajamos (ramas, PR, DoD) | [CONTRIBUTING.md](CONTRIBUTING.md) y [docs/workflow/](docs/workflow/) |
| Trabajar con agentes de IA | [docs/workflow/agentes-ia.md](docs/workflow/agentes-ia.md) |

## Primeros pasos

Requisitos: Docker, Docker Compose, Python 3.12+ y Node 20+.

```bash
cp .env.example .env
make up          # Postgres, MinIO (S3 local), Mailpit y backend
make test        # tests del backend
make help        # todos los comandos
```

API en http://localhost:8000 (docs en `/docs`). Mailpit en http://localhost:8025. Consola de MinIO en http://localhost:9001.

## Cómo trabajamos, en breve

1. Toda tarea sale de una **historia** en `docs/stories/` (con su issue en GitHub).
2. Rama corta desde `main`: `feat/E04-03-asignar-orden`.
3. Commits con Conventional Commits, PR chico, CI en verde, squash merge.
4. Las historias y las reglas de dominio las valida el analista de negocio antes de implementarse.

Detalle completo en [CONTRIBUTING.md](CONTRIBUTING.md).

## Estado

Fase 1 en definición. El alcance vigente y lo que sigue sin decidir está en [docs/stories/README.md](docs/stories/README.md) y [docs/domain/decisiones-pendientes.md](docs/domain/decisiones-pendientes.md).
