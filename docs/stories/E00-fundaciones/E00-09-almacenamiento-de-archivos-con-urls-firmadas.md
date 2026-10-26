---
id: E00-09
title: "Almacenamiento de archivos con URLs firmadas"
epic: E00
phase: 1
priority: must
status: draft
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

1. **Dado:** un usuario autorizado. **Cuando:** pide subir un archivo. **Entonces:** recibe una URL firmada de corta duración y el cliente sube directo al bucket.
2. **Dado:** un archivo subido. **Cuando:** se confirma la subida. **Entonces:** la base guarda solo la clave del objeto, el tipo y el tamaño.
3. **Dado:** un archivo. **Cuando:** un usuario sin permiso pide descargarlo. **Entonces:** recibe 403 y nunca una URL válida.
4. **Dado:** una URL firmada. **Cuando:** pasa su tiempo de vida. **Entonces:** deja de funcionar.
5. **Dado:** un archivo mayor al límite o de un tipo no permitido. **Cuando:** se pide subirlo. **Entonces:** se rechaza con un mensaje claro.

## Notas técnicas

- Local: MinIO. Nube: bucket del proveedor elegido en E00-05. Límite y tipos permitidos configurables (imágenes JPEG, PNG y WebP; PDF).
- La subida directa permite reintentos desde la PWA, necesarios si se corta la conexión (E05-13).
