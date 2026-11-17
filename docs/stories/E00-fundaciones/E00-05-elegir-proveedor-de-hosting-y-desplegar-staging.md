---
id: E00-05
title: "Elegir proveedor de hosting y desplegar staging"
epic: E00
phase: 1
priority: must
status: done
roles: [dev]
size: M
areas: [infra]
depends_on: [E00-01]
blocked_by: []
assumes: [D-006]
---

# E00-05 Elegir proveedor de hosting y desplegar staging

## Historia

**Como** equipo de desarrollo, **quiero** elegir el proveedor de hosting con los criterios del ADR 0004 y desplegar un entorno de staging, **para** tener un entorno real donde probar cada cambio.

## Criterios de aceptación

1. **Dado:** los criterios del ADR 0004. **Cuando:** se comparan al menos dos proveedores. **Entonces:** queda documentada la elección y el costo mensual estimado con fecha de cotización.
2. **Dado:** un merge a `main`. **Cuando:** termina CI. **Entonces:** staging se despliega solo y `GET /health` responde ok.
3. **Dado:** staging. **Cuando:** se revisan las cuentas. **Entonces:** el hosting, la base y el bucket están a nombre de la empresa cliente (o con un plan de traspaso documentado).
4. **Dado:** el despliegue. **Cuando:** se revisan variables. **Entonces:** ninguna credencial está en el repositorio.

## Decisiones tomadas

Por Gonza, el 2026-10-27, para que el cliente pruebe online el 2026-10-30 y lo use desde el 2026-11-06:

- **Render**, región Virginia, planes pagos (la base gratuita se borra a los 30 días). El costo se habla con el cliente fuera del repo (`D-006`).
- **Un solo entorno por ahora, que es producción**: los datos de la prueba siguen para el uso real. El criterio 2 se cumple sobre ese entorno; un staging aparte queda para después, junto con E00-06.

## Notas técnicas

- `render.yaml` (Blueprint) con la base, la API (Docker, migraciones al arrancar, salud en `/health/ready`) y los dos frontends como sitios estáticos. Paso a paso en `docs/workflow/despliegue.md`. ADR 0004 actualizado.
- Despliegue automático con cada merge a `main` (que solo recibe lo que pasó el CI).
- La API no arranca en producción sin una `APP_SECRET_KEY` real (32 caracteres o más) y los errores de configuración no muestran valores. `DATABASE_URL` se acepta como la da Render (`postgres://`, `sslmode=`).
- `python -m app.create_admin`: primer administrador de una base vacía, con la contraseña por teclado; se niega si ya hay uno.
- Cerrada el 2026-11-17, revisado en Render:
  - Criterio 1: Render elegido con los criterios del ADR 0004; el costo se habla fuera del repositorio (`D-006`).
  - Criterio 2: sobre producción, el único entorno. Los servicios tienen *Auto-Deploy* con cada merge a `main` (el último, `3224af8` de #290) y `/health/ready` responde `{"status":"ready","database":"ok"}`. Staging aparte pasa a E00-06.
  - Criterio 3: las cuentas de Render y Cloudflare R2 están a nombre de MendoData. Plan de traspaso al cliente en `docs/workflow/despliegue.md` ("Traspaso de las cuentas al cliente"), a hacer antes de que el cliente empiece a usar el sistema.
  - Criterio 4: las claves están solo en las variables de Render; gitleaks las busca en el CI.
- Los servicios se crearon a mano en el panel, no con el Blueprint: Render no lee `render.yaml`, que queda como referencia. Copia y mantenimiento corren en un solo cron, `vab-ot-backup` (#290).
