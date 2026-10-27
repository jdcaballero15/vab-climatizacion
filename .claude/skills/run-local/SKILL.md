---
name: run-local
description: Levanta el entorno local completo de OT Platform (base, bucket, mail de prueba, API con migraciones y datos de prueba, app de administración y app del técnico) y comprueba que funciona. Usar cuando se pida correr, arrancar o probar la app localmente.
---

# Correr OT Platform en local

Servicios en Docker Compose: `db` (Postgres 16), `minio` (bucket S3 compatible), `mailpit` (mail de prueba) y `backend`. Las dos apps web (`web-admin` y `pwa-tecnico`) corren fuera de Docker con Vite.

## Pasos

### 1. Backend y servicios

1. Copiar variables: `cp .env.example .env` (el `.env` no se commitea ni se lee desde los agentes).
2. Levantar: `make up` (sin `make`: `docker compose up -d --build`).
3. Aplicar migraciones (la base arranca vacía y el backend no las corre solo):
   `docker compose exec backend alembic upgrade head`
4. Cargar datos de prueba ficticios (solo en una base vacía; la contraseña se pasa por variable y vale para todos los usuarios):
   `docker compose exec -e SEED_PASSWORD=<contraseña> backend python -m app.demo_data`
   Crea `admin@ot-demo.com`, `direccion@ot-demo.com` y `tecnico1@ot-demo.com` a `tecnico4@ot-demo.com`.
5. Comprobar la API: `curl -s http://localhost:8000/health` debe responder `{"status":"ok"}`.

### 2. Apps web

En dos terminales distintas:

```bash
cd web-admin   && npm ci && npm run dev -- --port 5173 --strictPort
cd pwa-tecnico && npm ci && npm run dev -- --port 5174 --strictPort
```

### 3. Dónde mirar

| Qué | URL |
|---|---|
| App de administración | http://localhost:5173 |
| App del técnico | http://localhost:5174 |
| Documentación de la API | http://localhost:8000/docs |
| Mail de prueba (Mailpit) | http://localhost:8025 |
| Consola de MinIO | http://localhost:9001 |

Comprobación mínima: iniciar sesión con un usuario de prueba en cada app y recargar: tiene que seguir adentro. Desde la terminal, por el proxy de Vite:
`curl -s -X POST http://localhost:5173/api/auth/login -H 'Content-Type: application/json' -d '{"email":"admin@ot-demo.com","password":"<contraseña>"}' -D -` debe dar `200` y un `set-cookie: ot_refresh=...; HttpOnly; Path=/api/auth`.

### 4. Bajar

`make down` (o `docker compose down`). Los datos quedan en el volumen `db-data`; para empezar de cero: `docker compose down -v`.

## Trampas conocidas

- **La base local usa el puerto 5433** (no el 5432) a propósito: así un Postgres instalado en la máquina no se confunde con el de Docker, un error difícil de detectar porque `localhost` responde igual. Desde el host: `postgresql+asyncpg://ot:ot@localhost:5433/ot`.
- **Las dos apps llaman a la API por `/api`** y Vite la reenvía a `http://localhost:8000` sin el prefijo (ADR 0010: la cookie de la sesión tiene que ser del mismo sitio). No les pases `VITE_API_URL`: con la API en otra dirección, la sesión no sobrevive a una recarga. Si el backend corre en otro puerto: `API_PROXY_TARGET=http://localhost:<puerto>`.
- **Sin Docker** (Postgres instalado en la máquina, en el puerto 5433): migrar con `cd backend && .venv/bin/alembic upgrade head` y levantar la API con `.venv/bin/uvicorn app.main:app --port 8000`, con las variables del `.env` cargadas (ver más abajo). Las apps, igual que en el paso 2.
- **Puertos ocupados por otros proyectos** (5433, 5173, 5174): `--strictPort` hace que Vite falle en lugar de saltar a otro puerto en silencio. Ojo: si el puerto está ocupado, `curl` igual responde 200, pero con la app de otro proyecto. Para usar otros puertos sin tocar el repo, crear un `docker-compose.override.yml` (anotarlo en `.git/info/exclude`):
  ```yaml
  services:
    db:
      ports: !override
        - "5436:5432"
    backend:
      environment:
        CORS_ORIGINS: http://localhost:5180,http://localhost:5181
  ```
  y levantar las apps con `--port 5180` y `--port 5181`. Si cambian los puertos de las apps, hay que cambiar `CORS_ORIGINS` o el login falla por CORS.
- **En Windows no viene `make`.** Usar los comandos de `docker compose` directamente (están al lado de cada paso).
- **El `.env` no se carga solo** fuera de Docker. Si corrés `uvicorn` a mano: `set -a && source .env && set +a`.
- **Cambios en dependencias** (`pyproject.toml`) requieren `docker compose build backend`.
- **`make seed` corre fuera de Docker** y apunta a `db:5432`, que no existe desde el host. Es más simple correr el generador dentro del contenedor (paso 4).
- Datos de prueba siempre ficticios. Nunca cargar una exportación real de Persat.

Si algo de esto falla distinto, anotarlo acá: este archivo se actualiza con cada trampa nueva.
