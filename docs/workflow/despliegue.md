# Despliegue en Render

Cómo se publica el sistema en Render (E00-05, ADR 0004) y cómo se cargan los datos iniciales. Todo lo que se crea está en `render.yaml` (Blueprint): la base, la API, la administración y la app del técnico. El costo y los datos de la cuenta se gestionan fuera del repositorio (`D-006`).

Hoy hay **un solo entorno**, que es el de producción. Staging y la publicación por tag con aprobación (E00-06) llegan después.

## Qué crea el Blueprint

| Servicio | Tipo | Qué es |
|---|---|---|
| `vab-ot-db` | Postgres 16 | La base. Solo acepta conexiones desde Render, salvo que se habilite una IP (ver importación). |
| `vab-ot-api` | Web, Docker (`backend/Dockerfile`) | La API. Corre las migraciones al arrancar. Chequeo de salud en `/health/ready`. |
| `vab-ot-admin` | Sitio estático (`web-admin`) | La administración, para la PC de la oficina. |
| `vab-ot-tecnico` | Sitio estático (`pwa-tecnico`) | La app del celular de cada escuadrilla. |

Variables de la API: `APP_ENV=production`, `APP_SECRET_KEY` (la genera Render; la API no arranca en producción sin una clave real), `DATABASE_URL` (la conecta Render) y `CORS_ORIGINS` (las direcciones de los dos sitios). Los sitios reciben `VITE_API_URL` al construirse.

Región: Virginia (Render no tiene región en Sudamérica).

## Primera vez

1. **Cuenta (la persona responsable, no el agente).** Crear la cuenta de Render a nombre de la empresa cliente, o anotar el plan de traspaso. Cargar el medio de pago y conectar el repositorio de GitHub.
2. **Crear todo.** En Render: *New* > *Blueprint*, elegir el repositorio y la rama `main`. Render lee `render.yaml` y muestra los cuatro servicios con sus planes. Confirmar.
3. **Revisar las direcciones.** Si un nombre estaba ocupado, Render le agrega un sufijo (por ejemplo `vab-ot-api-x1y2`). En ese caso, corregir `CORS_ORIGINS` en la API y `VITE_API_URL` en los dos sitios con las direcciones reales, y volver a desplegar.
4. **Comprobar la API.** `https://<api>/health/ready` tiene que responder `{"status":"ready","database":"ok"}`.
5. **Crear el primer administrador.** En la API: *Shell*, y ahí:

   ```bash
   python -m app.create_admin --email <correo> --nombre "<nombre y apellido>"
   ```

   Pide la contraseña dos veces (no se escribe en la línea de comandos). Se niega si ya hay un administrador. Los demás usuarios se crean desde la administración (*Usuarios*), y las escuadrillas desde *Escuadrillas*.

## Importar clientes y equipos de Persat

Se corre **desde la máquina que tiene los archivos**, así los archivos con datos reales no se suben a ningún lado. Reglas en `docs/domain/migracion-persat.md`.

1. En la base (`vab-ot-db` > *Networking*), agregar la IP pública de esa máquina a la lista de acceso.
2. Copiar la *External Database URL* de la base. No se guarda en ningún archivo del repositorio.
3. Primero la prueba, que no guarda nada:

   ```bash
   cd backend
   DATABASE_URL='<external url>?sslmode=require' python -m app.persat_import \
     --clientes ../persat-export/<clientes>.xlsx --equipos ../persat-export/<equipos>.xlsx
   ```

4. Si las cantidades dan bien, lo mismo con `--aplicar`. Se puede repetir: lo ya importado no se duplica.
5. **Sacar la IP de la lista de acceso.**

## Cada cambio

Un merge a `main` despliega solo los servicios que cambiaron (a `main` solo llega lo que pasó el CI en su PR). La API corre las migraciones al arrancar; si una migración falla, la versión nueva no arranca y Render sigue con la anterior.

## Pendiente

- Backups con prueba de restauración: E00-07.
- Staging aparte y publicación por tag con aprobación: E00-05 y E00-06.
- Bucket para fotos y firmas: E00-09.
