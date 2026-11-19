# Ambiente develop - diseño

Fecha: 2026-11-15. Estado: aprobado el 2026-11-19, con un cambio: los servicios de Render van en un **workspace aparte y sin tarjeta**, para que develop no consuma los cupos de producción ni pueda generar un cobro. La decisión queda en el ADR 0011.

## Para qué

Hoy hay dos ambientes: el local y producción. Cada merge a `main` se publica solo en producción, con los datos reales del cliente. El objetivo es tener un ambiente **develop** donde Juan y su socio prueben los cambios ya desplegados antes de que lleguen al cliente.

## Objetivos

- Un ambiente develop en internet, con la administración, la app del técnico y la API, que se despliega solo desde la rama `develop`.
- Un paso explícito para publicar en producción: un PR de `develop` a `main`.
- Costo cero.

## Fuera de alcance

- Cambiar cómo se despliega producción: sigue publicándose sola desde `main`.
- Publicación por tag con aprobación y rollback automático (E00-06). Puede venir después sobre esta base.
- Crons en develop (copia nocturna y mantenimiento): no tienen plan gratis. El mantenimiento se genera a mano con "Generar ahora".
- Un ambiente por PR (*Preview Environments* de Render): es pago.

## Lo que no puede pasar

- Que develop toque datos o archivos de producción: la base, el bucket y las claves son distintos.
- Que develop tenga datos reales. Solo datos ficticios (`make seed`), nunca copias de producción.
- Que el armado de develop rompa o frene producción.
- Que aparezca un costo mensual.

## Enfoques considerados

| Enfoque | Qué implica | Por qué sí o no |
|---|---|---|
| **A. Rama `develop`** (elegido) | `feat/...` -> PR a `develop` -> se despliega en develop -> PR `develop` -> `main` -> producción | Es lo que el equipo espera de "develop". Producción no cambia. Contra: hay que acordarse de pasar `develop` a `main` y de traer a `develop` los arreglos urgentes hechos sobre `main`. |
| B. `main` -> develop, producción por tag | Producción se despliega con un tag y una aprobación (E00-06) | Más ordenado, pero hay que sacar el despliegue automático de producción y armar un workflow de aprobación: más trabajo y más riesgo sobre producción. |
| C. Un ambiente por PR | *Preview Environments* de Render | Descartado por costo. |

Juan eligió A el 2026-11-15.

## Diseño

### Ramas y flujo

```
feat/... --PR (CI)--> develop --(autoDeploy)--> ambiente develop
                          |  se prueba
                          +--PR (CI)--> main --(autoDeploy)--> producción
```

- `develop` se crea desde `main` y pasa a ser la rama base de todo el trabajo nuevo: las ramas `feat/`, `fix/` y `docs/` salen de `develop` y vuelven a `develop` por PR.
- Para publicar: un PR de `develop` a `main`, titulado `chore(release): <resumen>`, mergeado con *merge commit* (sin squash), así las dos ramas comparten la historia.
- **Arreglo urgente de producción:** rama `fix/...` desde `main`, PR a `main`, y después un PR de `main` a `develop` para no perderlo.
- La rama por defecto de GitHub pasa a ser `develop`, así los PR nuevos apuntan ahí sin pensar.

### Servicios de develop

Archivo aparte, `render.develop.yaml`, para que el Blueprint de producción (`render.yaml`) no cambie. Se crea un Blueprint nuevo en Render apuntando a ese archivo y a la rama `develop`.

| Servicio | Tipo y plan | Notas |
|---|---|---|
| `vab-ot-dev-api` | Web, Docker, **free** | Misma imagen (`backend/Dockerfile`). Se duerme a los 15 minutos sin uso y tarda ~1 minuto en despertar. `branch: develop`, `autoDeploy: true`, salud en `/health/ready`. |
| `vab-ot-dev-admin` | Sitio estático, gratis | Igual que `vab-ot-admin`, con la regla `/api/*` hacia `vab-ot-dev-api`. |
| `vab-ot-dev-tecnico` | Sitio estático, gratis | Igual que `vab-ot-tecnico`, con la regla `/api/*` hacia `vab-ot-dev-api`. |

Variables de la API de develop:

- `APP_ENV=develop`: el código solo trata distinto el valor `production`, así que develop puede cargar datos ficticios con `make seed`.
- `APP_SECRET_KEY`: la genera Render.
- `DATABASE_URL`: la de Neon (`sync: false`, se carga a mano).
- `CORS_ORIGINS`: las direcciones de los dos sitios de develop.
- `S3_*`: el bucket de develop.

### Base: Neon gratis

- Un proyecto en Neon (plan gratis, región AWS us-east-1, cerca de Virginia), con la versión de Postgres más cercana a la de producción que ofrezca Neon.
- No vence, a diferencia de la base gratis de Render (30 días). Límite de 0,5 GB, que alcanza para datos ficticios. Se suspende sin uso y despierta en segundos.
- Las migraciones corren solas cuando arranca la API, igual que en producción.
- **Datos:** primer administrador con `python -m app.create_admin` y datos ficticios con `make seed`, los dos **desde la máquina local** con la URL de Neon. El plan gratis de Render no tiene *Shell*.

### Archivos: bucket `vab-ot-files-dev` en R2

- Bucket nuevo en la misma cuenta, privado, con CORS para los dos sitios de develop.
- Token propio, *Object Read & Write*, **solo** para `vab-ot-files-dev`.
- Sin bucket lock: las fotos de develop se pueden borrar.
- Entra en los 10 GB gratis de R2 junto con producción. Si develop crece, se vacía el bucket.

### Cambios en el repositorio

1. `render.develop.yaml` con los tres servicios.
2. CI: `push` también en `develop` (`.github/workflows/ci.yml`). Los PR ya corren con cualquier rama base.
3. Hooks de Claude Code: `develop` protegida igual que `main` en `guard_bash.py` y `guard_edit.py`, con su caso en `test_guards.sh`.
4. Documentación:
   - `CLAUDE.md` y `CONTRIBUTING.md`: las ramas salen de `develop`, y el flujo de publicación y de arreglos urgentes.
   - `docs/workflow/despliegue.md`: sección "Ambiente develop" con el paso a paso.
   - ADR 0011 con la decisión.
   - Nota en E00-05 y E00-06.
5. `.env.example`: sin cambios (no hay variables nuevas).

### Pasos manuales (una persona, no el agente)

- GitHub: crear `develop` desde `main`, protegerla igual que `main` (PR obligatorio y CI en verde) y ponerla como rama por defecto.
- Neon: crear el proyecto y copiar la URL de conexión.
- Cloudflare: crear el bucket, el CORS y el token.
- Render: *New* > *Blueprint* con `render.develop.yaml` y la rama `develop`, y cargar las variables.
- Cargar el administrador y los datos ficticios desde local.

### Efectos de cambiar la rama por defecto a `develop`

- **Issues:** GitHub cierra un issue con "Cierra #N" cuando el PR entra en la rama por defecto. Con `develop` por defecto, el issue se cierra al llegar a develop, no a producción. Para este equipo alcanza (la historia está terminada cuando pasó las pruebas). Se anota en el ADR.
- **Sincronización de historias** (`stories-sync.yml`, en `push` a `main`): sigue en `main`, así que los issues se actualizan cuando se publica en producción.
- **Dependabot:** abre sus PR contra `develop`, que es lo que se quiere.

## Qué decide quien lo implementa

- Nombres exactos y texto de los documentos, siguiendo las convenciones del repo.
- Si Render le agrega un sufijo a algún nombre de servicio: corregir `CORS_ORIGINS` y las reglas `/api/*` con las direcciones reales, como en producción.

## Decisiones tomadas por Claude (a revisar)

- Neon en lugar de la base gratis de Render, para no recrearla cada 30 días.
- `APP_ENV=develop` en vez de `production`, para poder cargar datos ficticios.
- Un archivo de Blueprint aparte, para no tocar `render.yaml`.
- `develop` como rama por defecto de GitHub.
- Publicación con *merge commit* y arreglos urgentes que vuelven a `develop` por PR.
