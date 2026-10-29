---
id: E00-07
title: "Backups y prueba de restauración"
epic: E00
phase: 1
priority: must
status: in_progress
roles: [dev]
size: S
areas: [infra]
depends_on: [E00-05]
blocked_by: []
assumes: []
---

# E00-07 Backups y prueba de restauración

## Historia

**Como** equipo de desarrollo, **quiero** copias diarias de la base y que las fotos y firmas no se puedan borrar, con una prueba de restauración documentada, **para** no perder órdenes, cierres ni firmas ante un error, una caída o una clave filtrada.

## Criterios de aceptación

1. **Dado:** la base de producción. **Cuando:** pasa una noche. **Entonces:** hay una copia nueva de la base (`pg_dump`) en un bucket aparte, `vab-ot-backups`, y las de más de 30 días se borran solas.
2. **Dado:** la base de producción. **Cuando:** hay que volver a un momento de los últimos 3 días. **Entonces:** se puede, con la recuperación a un momento puntual de Render (incluida en la base paga).
3. **Dado:** una copia nocturna. **Cuando:** se restaura en una base aparte. **Entonces:** las migraciones están al día y las cantidades de órdenes, cierres y archivos coinciden con las de la copia.
4. **Dado:** la restauración. **Cuando:** se completa. **Entonces:** queda el paso a paso en `docs/workflow/backups.md`, con la fecha de la última prueba.
5. **Dado:** una foto o una firma en el bucket (`closures/`). **Cuando:** alguien intenta borrarla o sobrescribirla, con la API o con las claves del bucket. **Entonces:** R2 lo rechaza (bucket lock sin vencimiento).
6. **Dado:** el trabajo de copia. **Cuando:** falla. **Entonces:** Render avisa por correo (notificación de falla del cron job).

## Fuera de alcance

- Copias de las fotos y firmas en otro proveedor: con el lock no se pueden borrar ni pisar, y R2 replica los datos dentro de Cloudflare.
- Versionado del bucket: R2 no lo tiene (la API de S3 de R2 no implementa `PutBucketVersioning`). Lo reemplaza el lock del criterio 5.
- Restauración automática o un entorno de staging (E00-06).

## Notas técnicas

- **Trabajo de copia:** cron job de Render en `render.yaml` (`type: cron`, todas las noches, por ejemplo `0 7 * * *` en UTC, las 4 de Argentina), con `DATABASE_URL` desde `vab-ot-db`. Corre `pg_dump --format=custom` con el cliente de Postgres 16 y sube el archivo con `boto3` (ya es dependencia). Cuesta como mínimo US$ 1 por mes.
- **Bucket `vab-ot-backups`:** aparte del de archivos, privado, con su propio token (*Object Read & Write* solo para ese bucket). Variables del cron: `BACKUP_S3_ENDPOINT_URL`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY`, `BACKUP_S3_BUCKET`, cargadas en Render, nunca en el repo. Regla de ciclo de vida: borrar a los 30 días. Lock de 30 días, así una clave filtrada no puede borrar las copias antes de tiempo.
- **Lock de `closures/`:** la app nunca borra ni sobrescribe fotos ni firmas. Cada subida usa una clave nueva (`closures/<uso>/<uuid>`), y si se pierde la respuesta del `PUT`, la PWA pide otra subida. `check_storage` usa `checks/`, fuera del lock.
- Las copias tienen datos reales: no se bajan al repositorio ni se pegan en el chat. La prueba de restauración se hace contra una base temporal de Render, que se borra al terminar.
- Repetir la prueba de restauración cada trimestre.
- Se implementa con Render andando (E00-05).

## Supuestos confirmados

- 30 días de copias nocturnas alcanzan (Gonza, 2026-10-29, al mergear el refinamiento).
- Lock sin vencimiento sobre las fotos y firmas (ídem).

## Notas de implementación

- `python -m app.backup_db` (criterio 1): `pg_dump --format=custom` y subida a `db/<fecha y hora UTC>.dump` en el bucket de copias, con las filas de cada tabla en los metadatos del objeto (`table-counts`). Configuración `BACKUP_S3_*`, aparte de la del bucket de archivos.
- `python -m app.restore_check --destino <url>` (criterio 3): baja la última copia (o `--clave`), la restaura con `pg_restore` en una base vacía (se niega si tiene tablas) y compara la migración con la última y las filas de cada tabla con las de la copia.
- La imagen del backend trae el cliente de Postgres 16 de PGDG. El CI la construye (job `backend-image`) y comprueba que `pg_dump` sea 16.
- `render.yaml`: cron `vab-ot-backup` a las 07:00 UTC, misma imagen que la API con otro comando. La API recibe un token de solo lectura del bucket de copias para la prueba de restauración.
- Pasos de R2 (bucket de copias, regla de 30 días, locks) en `docs/workflow/despliegue.md`; recuperación y prueba de restauración en `docs/workflow/backups.md` (criterios 2, 4, 5 y 6).
- Tests en `tests/test_backup.py` con Postgres y MinIO reales: crean bases temporales, así que el rol de la base necesita `CREATEDB` (en el CI y en Docker ya lo tiene).
- **Queda `in_progress`** hasta que en Render corra la primera copia y la primera prueba de restauración, con la fecha anotada en `backups.md`.
