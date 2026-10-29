# Backups y restauración

Cómo se protegen la base y los archivos en producción, y cómo se prueba la restauración (E00-07). La creación de los buckets y los servicios está en [despliegue.md](despliegue.md).

**Última prueba de restauración:** todavía no se hizo. Repetirla cada trimestre y anotar acá la fecha, la copia usada y el resultado.

## Qué hay

| Qué | Cómo | Hasta cuándo atrás |
|---|---|---|
| Base, recuperación a un momento puntual | Incluida en la base paga de Render | 3 días (plan Hobby; 7 en Pro) |
| Base, copia nocturna | Cron `vab-ot-backup`: `pg_dump` al bucket `vab-ot-backups`, en `db/<fecha y hora UTC>.dump` | 30 días |
| Fotos y firmas | Bucket lock sin vencimiento sobre `closures/` en `vab-ot-files`: R2 no deja borrarlas ni sobrescribirlas | Siempre |

- La copia nocturna corre a las 4 de la mañana de Argentina (07:00 UTC). Guarda en el objeto cuántas filas tenía cada tabla, para comprobar la restauración.
- `vab-ot-backups` tiene una regla que borra las copias de más de 30 días y un lock de 30 días: ni con una clave filtrada se pueden borrar antes.
- R2 no tiene versionado. Lo reemplaza el lock: la app nunca borra ni sobrescribe fotos ni firmas (cada subida usa una clave nueva).
- Si la copia falla, Render manda un correo (*Workspace settings* > *Notifications*: avisos de fallas de cron jobs activados).
- Las copias tienen datos reales: no se bajan a una máquina ni se pegan en el chat.

## Volver a un momento de los últimos 3 días

Para un error descubierto enseguida (por ejemplo, datos borrados o pisados hace unas horas).

1. En Render: `vab-ot-db` > *Recovery* > *Restore*. Elegir la fecha y hora (no puede ser de los últimos 10 minutos). Render crea una **base nueva** con ese estado; la original no se toca.
2. Revisar la base nueva. En `vab-ot-api` > *Shell* (la imagen trae `psql`):

   ```bash
   psql '<internal url de la base nueva>' -c 'SELECT number, status, updated_at FROM work_order ORDER BY updated_at DESC LIMIT 10'
   ```
3. Si está bien, en `vab-ot-api` y `vab-ot-backup` > *Environment*, cambiar `DATABASE_URL` por la *Internal Database URL* de la base nueva y volver a desplegar. Si el Blueprint se vuelve a sincronizar, actualizar también `render.yaml` con el nombre de la base nueva.
4. Cuando todo ande, borrar la base vieja.

## Restaurar una copia nocturna (y la prueba trimestral)

Para un error descubierto días después, o para la prueba de cada trimestre. Se hace todo dentro de Render: la copia no sale de ahí.

1. Crear una base temporal: *New* > *Postgres*, nombre `vab-ot-restore-prueba`, Postgres 16, región Virginia, plan *Free*. Copiar su *Internal Database URL*.
2. En `vab-ot-api` > *Shell*:

   ```bash
   python -m app.restore_check --destino '<internal url de la base temporal>'
   ```

   Baja la última copia (o la de `--clave db/<fecha>.dump`), la restaura y comprueba que la migración sea la última y que cada tabla tenga las mismas filas que al copiarla. Se niega si la base de destino no está vacía. Tiene que terminar con `Restauración OK` y la lista de tablas.
3. Para la prueba trimestral: anotar arriba la fecha, la copia y el resultado, y **borrar la base temporal**.
4. Para recuperar datos de verdad: en vez de borrarla, apuntar la API a esa base como en el paso 3 de la sección anterior, o sacar de ahí solo lo que haga falta.

Si una copia es de una migración vieja (la API se actualizó después), `restore_check` lo avisa: restaurar la copia igual sirve para sacar datos, pero para usarla como base hay que migrarla (`alembic upgrade head` con esa `DATABASE_URL`).

## Correr la copia a mano

En `vab-ot-backup` > *Trigger Run*. O en local, contra la base y el MinIO locales:

```bash
cd backend
.venv/bin/python -m app.backup_db
```

En local el bucket es `ot-backups` en MinIO; crearlo una vez desde la consola de MinIO (`http://localhost:9001`).
