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

Variables de la API: `APP_ENV=production`, `APP_SECRET_KEY` (la genera Render; la API no arranca en producción sin una clave real), `DATABASE_URL` (la conecta Render) y `CORS_ORIGINS` (las direcciones de los dos sitios). Los sitios llaman a la API por `/api` de su propia dirección (`VITE_API_URL=/api`): una regla de cada sitio reenvía `/api/*` a la API sin el prefijo. Así la cookie de la sesión es del mismo sitio y la sesión sobrevive a una recarga (ADR 0010, E01-07).

Región: Virginia (Render no tiene región en Sudamérica).

## Primera vez

1. **Cuenta (la persona responsable, no el agente).** Crear la cuenta de Render a nombre de la empresa cliente, o anotar el plan de traspaso. Cargar el medio de pago y conectar el repositorio de GitHub.
2. **Bucket en Cloudflare R2** (antes del Blueprint, porque la API pide sus datos). Ver [Bucket de archivos](#bucket-de-archivos-cloudflare-r2).
3. **Crear todo.** En Render: *New* > *Blueprint*, elegir el repositorio y la rama `main`. Render lee `render.yaml` y muestra los cuatro servicios con sus planes. Pide los valores que no están en el archivo: `S3_ENDPOINT_URL`, `S3_ACCESS_KEY` y `S3_SECRET_KEY` del paso anterior. Confirmar.
4. **Revisar las direcciones.** Si un nombre estaba ocupado, Render le agrega un sufijo (por ejemplo `vab-ot-api-x1y2`). En ese caso, corregir `CORS_ORIGINS` en la API con las direcciones reales de los sitios y, si el sufijo lo tiene la API, el destino de la regla `/api/*` de los dos sitios (*Redirects/Rewrites*). `VITE_API_URL` queda en `/api`. Volver a desplegar.
5. **Comprobar la API.** `https://<api>/health/ready` tiene que responder `{"status":"ready","database":"ok"}`, y lo mismo por la regla de cada sitio: `https://<sitio>/api/health/ready`.
6. **Crear el primer administrador.** En la API: *Shell*, y ahí:

   ```bash
   python -m app.create_admin --email <correo> --nombre "<nombre y apellido>"
   ```

   Pide la contraseña dos veces (no se escribe en la línea de comandos). Se niega si ya hay un administrador. Los demás usuarios se crean desde la administración (*Usuarios*), y las escuadrillas desde *Escuadrillas*.

7. **Comprobar la sesión por la regla `/api/*`.** En la administración, ingresar con ese usuario y recargar la página: tiene que entrar directo, sin pedir la contraseña. En las herramientas del navegador (*Red*), la llamada a `/api/auth/login` es un `POST` que responde `200` con un `Set-Cookie` `ot_refresh` (`HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/auth`). Cerrar sesión y recargar tiene que mostrar el login. Repetir en la app del técnico con un usuario de escuadrilla. Si la regla no deja pasar el `POST` o el `Set-Cookie`, la sesión se pierde al recargar: pasar al plan B del ADR 0010 (dominio propio con subdominios).

8. **Comprobar el bucket.** En la API: *Shell*, y ahí:

   ```bash
   python -m app.check_storage
   ```

   Sube un archivo de prueba con una URL firmada, lo lee y lo borra. Tiene que decir `Bucket OK`.

## Bucket de archivos (Cloudflare R2)

Fotos y firmas van a un bucket privado, nunca a la base (E00-09). La API firma URLs de 5 minutos para subir y bajar.

1. En Cloudflare: *R2* > *Create bucket*, nombre `vab-ot-files`, ubicación *Automatic* (o Norteamérica Este, cerca de la API). Sin acceso público.
2. *R2* > *Manage API tokens* > *Create API token*: permiso *Object Read & Write*, solo para el bucket `vab-ot-files`. Copiar *Access Key ID*, *Secret Access Key* y el endpoint (`https://<account id>.r2.cloudflarestorage.com`). Se cargan en Render (paso 3) y no se guardan en ningún archivo del repositorio ni se pegan en el chat.
3. En el bucket: *Settings* > *CORS policy*, para que los navegadores puedan subir directo:

   ```json
   [
     {
       "AllowedOrigins": ["https://vab-ot-admin.onrender.com", "https://vab-ot-tecnico.onrender.com"],
       "AllowedMethods": ["PUT", "GET"],
       "AllowedHeaders": ["Content-Type"],
       "MaxAgeSeconds": 3600
     }
   ]
   ```

   Si los sitios quedaron con sufijo, usar las direcciones reales.

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
