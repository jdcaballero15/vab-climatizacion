# ADR 0004: Hosting en PaaS con PostgreSQL administrado

**Estado:** Aceptado. Proveedor elegido el 2026-10-27: **Render** (E00-05).

## Contexto

La carga es mínima, pero perder órdenes o cobros es el peor escenario, y el sistema maneja datos personales (nombre, DNI y firma de clientes). Quien lo mantiene es una consultora chica. La propuesta al cliente dice que el sistema "es de ustedes, sin abono obligatorio".

## Decisión

- Contenedores Docker desplegados en un **PaaS** (Railway, Render o Fly.io).
- **PostgreSQL administrado**, con backups automáticos y restauración a un punto en el tiempo.
- **Bucket S3 compatible** (Cloudflare R2, Backblaze B2 o S3) para fotos, firmas y PDF.
- Las **cuentas de hosting, base y bucket se crean a nombre del cliente**, con MendoData como administrador.
- Dos entornos: staging (automático desde `main`) y producción (tag con aprobación).

## Criterios para elegir proveedor (E00-05)

1. Backups con restauración a un punto en el tiempo incluidos.
2. Región cercana (Sudamérica) si existe, por latencia.
3. Costo mensual en dólares estable y predecible. Se informa al cliente como referencia con cotización y fecha.
4. Cron jobs o scheduler nativo para los jobs mensuales.
5. Facilidad para migrar a otro proveedor o a un VPS (solo Docker y variables de entorno).

## Proveedor elegido

**Render**, decidido el 2026-10-27 para la prueba del cliente del 2026-10-30 y el uso real desde el 2026-11-06:

- Postgres administrado con backups, API en Docker y los dos frontends como sitios estáticos, todo descrito en `render.yaml` (Blueprint). Paso a paso en `docs/workflow/despliegue.md`.
- Región Virginia: Render no tiene región en Sudamérica (criterio 2 sin cumplir; la carga es baja).
- Planes pagos desde el inicio: la base gratuita se borra a los 30 días y el servicio gratuito se suspende sin uso.
- Por ahora un solo entorno (producción). Staging y la publicación por tag llegan después (E00-05, E00-06).
- Cumple el criterio 5: solo Docker y variables de entorno; `render.yaml` es lo único propio de Render.

## Alternativas descartadas

- **VPS único con Docker Compose**: el más barato, pero MendoData pasa a ser sysadmin del cliente (backups, parches, caídas).
- **AWS (ECS, RDS, S3)**: sobredimensionado para este volumen.

## Consecuencias

- El costo mensual es mayor que un VPS, a cambio de menos riesgo operativo.
- Al ser portable, si el costo molesta se mueve a un VPS sin reescribir.
- Hay un costo recurrente en dólares que no existía con Microsoft 365. Se tiene que hablar con el cliente antes de contratar (`D-006`).
