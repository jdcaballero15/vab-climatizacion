---
id: E00-09
title: "Almacenamiento de archivos con URLs firmadas"
epic: E00
phase: 1
priority: must
status: ready
roles: [dev]
size: M
areas: [backend, infra]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E00-09 Almacenamiento de archivos con URLs firmadas

## Historia

**Como** equipo de desarrollo, **quiero** un servicio de archivos sobre un bucket S3 compatible, con subida y descarga mediante URLs firmadas, **para** guardar fotos, firmas y PDF fuera de la base de datos.

## Criterios de aceptación

1. **Dado:** un usuario autorizado. **Cuando:** pide subir un archivo indicando tipo y tamaño. **Entonces:** recibe el id del archivo y una URL firmada de 5 minutos, y el cliente sube directo al bucket.
2. **Dado:** un archivo subido. **Cuando:** el cliente confirma la subida. **Entonces:** el servidor comprueba en el bucket que el objeto existe con el tipo y el tamaño declarados, y la base guarda solo la clave del objeto, el tipo, el tamaño, quién lo subió y cuándo.
3. **Dado:** una confirmación de un objeto que no está en el bucket, o que no coincide con lo declarado. **Cuando:** se procesa. **Entonces:** se rechaza (422) y el archivo no queda disponible para usarse.
4. **Dado:** un archivo. **Cuando:** un usuario sin permiso pide descargarlo. **Entonces:** recibe 403 (o 404 si no debe saber que existe) y nunca una URL válida.
5. **Dado:** una URL firmada. **Cuando:** pasa su tiempo de vida. **Entonces:** deja de funcionar.
6. **Dado:** un archivo mayor al límite o de un tipo no permitido. **Cuando:** se pide subirlo. **Entonces:** se rechaza con un mensaje claro y no se emite URL.
7. **Dado:** el bucket. **Cuando:** alguien pide un objeto sin firma. **Entonces:** no lo obtiene (bucket privado).

## Fuera de alcance

- Borrar del bucket los archivos pedidos y nunca usados en un cierre: va con los jobs programados (E00-11).
- Miniaturas o redimensionado en el servidor: la PWA comprime antes de subir (E05-06).
- Antivirus o análisis del contenido.

## Notas técnicas

- **Proveedor:** Cloudflare R2 en la nube (decidido por negocio el 2026-10-27). Local: MinIO (en Docker, o instalado con Homebrew si no hay Docker). El código usa la API S3 (`boto3`), así que cambia solo la configuración (`S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION=auto` en R2).
- **Subida con `PUT` firmado**, no con `POST` y política: R2 no soporta `POST` de formularios. `Content-Type` y `Content-Length` van firmados en la URL, así el bucket rechaza un archivo distinto del declarado. La confirmación (criterio 2) igual verifica con `HEAD`.
- Modelo `stored_file`: `id`, `object_key` (con prefijo por tipo de uso, por ejemplo `closures/photos/<uuid>`, sin datos personales en la clave), `content_type`, `size_bytes`, `uploaded_by`, `created_at`, `confirmed_at` (nulo hasta confirmar), `deleted_at`. Migración reversible y `data-model.dbml`.
- Endpoints genéricos en el backend (`POST /files` para pedir la subida, `POST /files/{id}/confirm`). La descarga la expone cada recurso dueño del archivo (por ejemplo el cierre en E05-06), que decide el permiso; el servicio de archivos solo firma.
- Límite 5 MB por archivo y tipos permitidos configurables: JPEG, PNG y WebP; PDF.
- **CORS del bucket:** permitir `PUT` desde los dos sitios (Render) y desde `localhost` en desarrollo. Se anota en `docs/workflow/despliegue.md` junto con la creación del bucket y las claves en R2 (las claves van en las variables de Render, nunca en el repo).
- La subida directa permite reintentos desde la PWA, necesarios si se corta la conexión (E05-13).
