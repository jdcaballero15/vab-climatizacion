# Despliegue en Render

Cómo se publica el sistema en Render (E00-05, ADR 0004) y cómo se cargan los datos iniciales. `render.yaml` (Blueprint) describe la base, la API, la copia nocturna, la administración y la app del técnico. El costo y los datos de la cuenta se gestionan fuera del repositorio (`D-006`).

**Cómo está hoy:** los servicios de producción se crearon **a mano** en el panel, sin el Blueprint, en una cuenta de MendoData (no del cliente; ver [Traspaso de las cuentas al cliente](#traspaso-de-las-cuentas-al-cliente)). Render no lee `render.yaml`: sirve de referencia de cómo va cada servicio (planes, comandos, horarios, variables), y cualquier cambio de servicio se hace a mano en el panel y se anota también en `render.yaml`.

Hoy hay **un solo entorno**, que es el de producción. Staging y la publicación por tag con aprobación (E00-06) llegan después.

## Servicios

| Servicio | Tipo | Qué es |
|---|---|---|
| `vab-ot-db` | Postgres 18 | La base. Solo acepta conexiones desde Render, salvo que se habilite una IP (ver importación). |
| `vab-ot-api` | Web, Docker (`backend/Dockerfile`) | La API. Corre las migraciones al arrancar. Chequeo de salud en `/health/ready`. |
| `vab-ot-backup` | Cron, Docker (misma imagen que la API) | Corrida nocturna (`python -m app.nightly_run`): copia de la base al bucket `vab-ot-backups` ([backups.md](backups.md)) y después las órdenes de mantenimiento de las visitas de la semana (E07-04). Un solo cron para pagar uno; cada paso corre aunque el otro falle. |
| `vab-ot-admin` | Sitio estático (`web-admin`) | La administración, para la PC de la oficina. |
| `vab-ot-tecnico` | Sitio estático (`pwa-tecnico`) | La app del celular de cada escuadrilla. |

Variables de la API: `APP_ENV=production`, `APP_SECRET_KEY` (la genera Render; la API no arranca en producción sin una clave real), `DATABASE_URL` (la conecta Render) y `CORS_ORIGINS` (las direcciones de los dos sitios). Los sitios llaman a la API por `/api` de su propia dirección (`VITE_API_URL=/api`): una regla de cada sitio reenvía `/api/*` a la API sin el prefijo. Así la cookie de la sesión es del mismo sitio y la sesión sobrevive a una recarga (ADR 0010, E01-07).

Región: Virginia (Render no tiene región en Sudamérica).

## Primera vez

1. **Cuenta (la persona responsable, no el agente).** Crear la cuenta de Render a nombre de la empresa cliente (si es una cuenta de MendoData, queda pendiente el [traspaso](#traspaso-de-las-cuentas-al-cliente)). Cargar el medio de pago y conectar el repositorio de GitHub.
2. **Buckets en Cloudflare R2** (antes del Blueprint, porque la API y el cron piden sus datos). Ver [Bucket de archivos](#bucket-de-archivos-cloudflare-r2) y [Bucket de copias](#bucket-de-copias-cloudflare-r2).
3. **Crear todo.** En Render: *New* > *Blueprint*, elegir el repositorio y la rama `main`. Render lee `render.yaml` y muestra la base y los cuatro servicios con sus planes. Pide los valores que no están en el archivo, del paso anterior: en la API `S3_ENDPOINT_URL`, `S3_ACCESS_KEY` y `S3_SECRET_KEY` (bucket de archivos) y `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_ACCESS_KEY` y `BACKUP_S3_SECRET_KEY` (token de **solo lectura** del bucket de copias); en `vab-ot-backup` los mismos tres `BACKUP_S3_*`, con el token de **lectura y escritura**. Confirmar. Si el Blueprint ya existía antes de sumar el cron, Render crea `vab-ot-backup` al sincronizar y esos valores se cargan a mano en *Environment*. Sin Blueprint (como en producción hoy), cada servicio se crea con *New* (*Postgres*, *Web Service*, *Cron Job*, *Static Site*) copiando de `render.yaml` el plan, `rootDir`, comandos, horario y variables.
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

9. **Comprobar la copia nocturna.** En `vab-ot-backup`: *Trigger Run*. En *Logs* tiene que decir `Copia OK: db/<fecha>.dump`. En *Workspace settings* > *Notifications*, dejar activados los avisos por correo de fallas de cron jobs. La prueba de restauración está en [backups.md](backups.md).

10. **Comprobar el mantenimiento.** En la misma corrida de `vab-ot-backup`, después de la copia, *Logs* tiene que decir `Órdenes generadas: N. Planes omitidos: M.` Si la copia falló, el mantenimiento corre igual y la corrida termina con `Falló: copia.`

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

4. En el bucket: *Settings* > *Bucket lock rules* > *Add rule*: prefijo `closures/`, retención **indefinida**. Así nadie puede borrar ni sobrescribir fotos ni firmas, ni con una clave filtrada (E00-07). No cubre `checks/`, donde `check_storage` sube y borra su archivo de prueba.

## Bucket de copias (Cloudflare R2)

Las copias nocturnas de la base van a otro bucket, con sus propios tokens (E00-07, [backups.md](backups.md)).

1. *R2* > *Create bucket*, nombre `vab-ot-backups`, misma ubicación que el de archivos. Sin acceso público y sin CORS (solo lo usan el cron y la API).
2. En el bucket: *Settings* > *Object lifecycle rules* > *Add rule*: borrar los objetos 30 días después de subidos.
3. En el bucket: *Settings* > *Bucket lock rules* > *Add rule*: sin prefijo, retención de 30 días.
4. Dos tokens en *R2* > *Manage API tokens*, los dos solo para `vab-ot-backups`:
   - *Object Read & Write*, para el cron `vab-ot-backup`.
   - *Object Read only*, para la API (la prueba de restauración solo baja copias).

   Igual que con el bucket de archivos: se cargan en Render (paso 3) y no se guardan en el repositorio ni se pegan en el chat. El endpoint es el mismo.

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

## Traspaso de las cuentas al cliente

El ADR 0004 pide que hosting, base y buckets queden a nombre del cliente. Hoy Render (`vab-ot-api`, `vab-ot-admin`, `vab-ot-tecnico`, `vab-ot-db`, `vab-ot-backup`) y Cloudflare R2 (`vab-ot-files`, `vab-ot-backups`) están en una cuenta de MendoData. Conviene hacer el traspaso **antes de que el cliente empiece a usar el sistema**: con pocos datos se mueve más rápido y no hay que cortar el trabajo diario.

Lo hace la persona responsable, con el cliente; el agente puede guiar en el panel, pero no crea cuentas ni carga claves.

1. **Cuentas del cliente.** La empresa crea su cuenta de Render y la de Cloudflare con un correo propio (no personal) y carga su medio de pago. Invita a MendoData como administrador en las dos.
2. **Repositorio.** Conectar GitHub a la cuenta nueva de Render, con acceso solo a este repositorio.
3. **Buckets.** En la cuenta nueva de Cloudflare, crear `vab-ot-files` y `vab-ot-backups` con sus reglas y tokens ([archivos](#bucket-de-archivos-cloudflare-r2), [copias](#bucket-de-copias-cloudflare-r2)). Si ya hay fotos o firmas, copiar el contenido de `vab-ot-files` del bucket viejo al nuevo, con las mismas rutas.
4. **Base.** En la cuenta nueva de Render, crear solo `vab-ot-db` (Postgres 18, mismo plan y región). Avisar que nadie use el sistema un rato y pasar los datos desde una máquina con `pg_dump` y `pg_restore` de la versión 18, habilitando su IP en las dos bases como en [Importar clientes y equipos de Persat](#importar-clientes-y-equipos-de-persat) y sacándola al terminar:

   ```bash
   pg_dump --format=custom --no-owner --file=traspaso.dump '<external url de la base vieja>?sslmode=require'
   pg_restore --no-owner --dbname='<external url de la base nueva>?sslmode=require' traspaso.dump
   ```

   El archivo tiene datos reales: borrarlo al terminar y nunca subirlo al repositorio.
5. **Servicios.** Crear la API, el cron y los dos sitios como en [Primera vez](#primera-vez), pasos 3 a 5, con las claves de los buckets nuevos y `APP_SECRET_KEY` nueva (las sesiones abiertas se cierran: hay que volver a entrar). La API encuentra la base ya migrada. Si los nombres quedaron con sufijo porque los viejos siguen ocupados, corregir `CORS_ORIGINS`, las reglas `/api/*` y el CORS de `vab-ot-files`. No hace falta crear otro administrador: los usuarios vienen con la base. Comprobar en la administración que están los clientes, equipos, órdenes y usuarios, y abrir una orden con foto.
6. **Comprobar** como en [Primera vez](#primera-vez), pasos 7 a 10 (sesión, bucket, copia y mantenimiento).
7. **Pasar a las escuadrillas y a la oficina las direcciones nuevas** si cambiaron (la app del técnico se reinstala desde la dirección nueva).
8. **Apagar lo viejo** recién después de una semana sin problemas: suspender los servicios de Render, borrar los tokens de R2 viejos y, cuando venzan las copias, `vab-ot-backups` viejo. El `vab-ot-files` viejo no se puede vaciar mientras tenga el lock indefinido sobre `closures/`: sacar esa regla recién cuando el contenido esté copiado y comprobado en el nuevo.

## Pendiente

- Traspaso de las cuentas al cliente (sección anterior).
- Staging aparte y publicación por tag con aprobación: E00-06.
