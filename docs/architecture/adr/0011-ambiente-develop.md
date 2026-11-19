# ADR 0011: Probar los cambios en un ambiente develop antes de publicarlos en producción

- **Estado:** Propuesto
- **Fecha:** 2026-11-19
- **Decide:** Juan (MendoData)
- **Áreas afectadas:** infra, docs, ia

---

## Contexto

Hoy hay dos ambientes: el local y producción (E00-05). Cada merge a `main` se publica solo en producción, donde el cliente ya trabaja con datos reales. No hay dónde probar un cambio ya desplegado (en Render, con el bucket y la sesión reales) antes de que lo vea el cliente.

Restricciones:

- **Costo cero.** El ambiente de pruebas no puede sumar un costo mensual, ni siquiera por pasarse de un cupo compartido con producción.
- Que no toque datos ni archivos de producción, y que no tenga datos reales (el repositorio es público y la Ley 25.326 aplica igual).
- Que armarlo no frene ni ponga en riesgo producción.

## Decisión

> Trabajamos sobre una rama `develop` que se despliega sola en un ambiente develop gratis, y publicamos en producción con un PR de `develop` a `main`.

- **Ramas.** `develop` sale de `main`, es la rama por defecto de GitHub y está protegida como `main` (PR obligatorio, `ci-ok` en verde, sin borrado ni force push). Las ramas `feat/`, `fix/`, `docs/` y `chore/` salen de `develop` y vuelven por PR con squash.
- **Publicar.** PR de `develop` a `main`, titulado `chore(release): <resumen>`, con *merge commit* (sin squash) para que las dos ramas compartan la historia. `main` se sigue publicando sola en producción, como hasta ahora.
- **Arreglo urgente.** Rama `fix/...` desde `main`, PR a `main`, y después un PR de `main` a `develop` para no perderlo.
- **Servicios.** `render.develop.yaml` (Blueprint aparte; `render.yaml` no cambia) con la API en el plan free y los dos sitios estáticos, desde `develop`, en un **workspace de Render aparte y sin tarjeta**: si se acaba un cupo gratis (horas, minutos de build, ancho de banda), el servicio se frena, pero nada se cobra ni se descuenta del cupo de producción.
- **Base.** Proyecto gratis de Neon (región AWS us-east-1), conexión directa. Las migraciones corren al arrancar la API, igual que en producción.
- **Archivos.** Bucket `vab-ot-files-dev` en R2, privado, sin lock, con un token solo para ese bucket.
- **Datos.** Solo ficticios (`python -m app.demo_data`), cargados desde una máquina local porque el plan free no tiene *Shell*. `APP_ENV=develop`: el código solo trata distinto `production`.
- **Sin crons** en develop: no tienen plan gratis. El mantenimiento se genera con "Generar ahora".

## Alternativas consideradas

| Alternativa | Ventajas | Por qué se descartó |
|---|---|---|
| `main` a develop y producción por tag con aprobación (E00-06) | Una sola rama, más ordenado | Hay que sacar el despliegue automático de producción y armar un workflow de aprobación: más trabajo y más riesgo sobre producción ahora. Puede venir después sobre esta base. |
| Un ambiente por PR (*Preview Environments* de Render) | Cada cambio se prueba aislado | Es pago. |
| Develop en el mismo workspace de Render que producción | Un solo panel | Comparte cupos con producción, que tiene tarjeta: pasarse se cobra. |
| Base gratis de Render | Todo en Render | Se borra a los 30 días: habría que recrearla y recargarla cada mes. |

## Consecuencias

**Positivas**
- Cada cambio se ve desplegado antes de que llegue al cliente.
- Producción se despliega igual que antes: nada cambia en su configuración.
- Develop no puede generar costo ni tocar datos de producción.

**Negativas o costo que aceptamos**
- La API de develop se duerme sin uso y tarda cerca de un minuto en despertar.
- Hay que acordarse de publicar (`develop` a `main`) y de traer a `develop` los arreglos urgentes.
- Con `develop` como rama por defecto, "Cierra #N" cierra el issue cuando el PR llega a develop, no a producción. Para este equipo alcanza: la historia está terminada cuando pasó las pruebas. La sincronización de historias (`stories-sync.yml`) sigue en `push` a `main`.

**Qué se vuelve más difícil de ahora en adelante**
- Cada cambio se compila dos veces (develop y producción). Se acepta porque develop tiene su propio cupo.
- Si un cupo gratis se acaba, develop queda frenado hasta el mes siguiente.

## Impacto en las reglas del repositorio

- [x] [`CLAUDE.md`](../../../CLAUDE.md): las ramas salen de `develop`; `develop` protegida como `main`
- [ ] [`docs/code-standards.md`](../../code-standards.md)
- [ ] `ALLOWED_TOPLEVEL` en `.claude/hooks/guard_edit.py` (carpeta nueva en la raíz)
- [x] `.github/workflows/ci.yml`: CI en `push` a `develop` y PR entre `develop` y `main`
- [ ] `.env.example`
- [x] Historias afectadas en `docs/stories/`: E00-06
- [x] Hooks `guard_bash.py` y `guard_edit.py`: `develop` protegida
- [x] `CONTRIBUTING.md` y `docs/workflow/despliegue.md`

## Referencias

- Diseño: `docs/superpowers/specs/2026-11-15-ambiente-develop-design.md`.
- E00-05 (despliegue en Render), E00-06 (producción por tag), ADR 0004 (hosting), ADR 0010 (sesión por `/api`).
