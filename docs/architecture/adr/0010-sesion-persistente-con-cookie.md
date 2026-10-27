# ADR 0010: Mantener la sesión entre recargas con el refresh token en una cookie httpOnly

- **Estado:** Propuesto
- **Fecha:** 2026-10-27
- **Decide:** Gonzalo Manresa (MendoData)
- **Áreas afectadas:** backend, web-admin, pwa-tecnico, infra

---

## Contexto

Desde E01-02 los dos tokens (acceso y refresco) viven en memoria: al recargar la página o al reabrir la app del celular hay que volver a ingresar. Era un criterio a propósito (riesgo XSS en un repositorio público) y quedó pendiente una decisión aparte.

Ahora hay fecha: el cliente prueba online el 30/10 y empieza a usarlo el 6/11. Un técnico que cierra la PWA entre una orden y otra, o una persona de la oficina que recarga la administración, no puede tener que escribir la contraseña cada vez.

Restricciones:

- En Render, la API y los dos sitios tienen direcciones distintas bajo `onrender.com`, que está en la lista de sufijos públicos: para el navegador son **sitios distintos**. Una cookie de la API en una llamada desde otro sitio es una cookie de terceros, que los navegadores bloquean cada vez más.
- No hay dominio propio por ahora.
- Lo que guarde el navegador no tiene que poder leerlo un script inyectado (XSS).

## Decisión

> Guardamos el refresh token en una cookie `httpOnly` y cada sitio llama a la API por su propia dirección, en `/api/*`, que reenvía las llamadas a la API.

- **Cookie:** la emiten `POST /auth/login` y `POST /auth/refresh`. Es `HttpOnly`, `Secure`, `SameSite=Strict`, vale solo para la ruta de sesión (`/api/auth`) y dura lo mismo que el refresh token en el servidor (30 días). En la base sigue guardándose solo el hash y se sigue rotando en cada renovación.
- **Mismo sitio:** cada sitio estático tiene una regla de Render que reenvía `/api/*` a la API, antes de la regla que manda todo a `index.html`. Los sitios se construyen con `VITE_API_URL=/api`. En local, el servidor de Vite hace lo mismo con su opción `proxy` hacia `localhost:8000`.
- **Al abrir la app:** el cliente llama a `POST /auth/refresh` sin cuerpo. Si la cookie es válida, recibe un access token y el usuario y entra directo; si no, muestra el login.
- **El access token** sigue en memoria y viaja en `Authorization: Bearer`. No cambia la autorización por rol (ADR 0006).
- **Cerrar sesión:** `POST /auth/logout` revoca el token y borra la cookie.
- **Compatibilidad:** mientras se migran los dos sitios, el backend sigue devolviendo `refresh_token` en el cuerpo y aceptándolo en `/auth/refresh` y `/auth/logout`. Cuando los dos usan la cookie, se saca del cuerpo: si no, un script inyectado podría pedir una renovación y leer el token de la respuesta. El despliegue se hace con el cuerpo ya limpio.
- **CSRF:** con `SameSite=Strict` la cookie no viaja desde otro sitio, y las rutas que la usan solo renuevan o cierran la sesión; no modifican datos del negocio.

## Alternativas consideradas

| Alternativa | Ventajas | Por qué se descartó |
|---|---|---|
| Refresh token en `localStorage` | Lo más simple; sin cambios en Render | Un script inyectado lo lee y se lleva una sesión de 30 días |
| Cookie `SameSite=None` directo a la API, sin `/api` | Sin reenvío | Es una cookie de terceros: Safari y el modo estricto de Chrome la bloquean, y la sesión se perdería sin aviso |
| Subdominios de un dominio propio (`api.`, `tecnico.`, `admin.`) | Mismo sitio sin reenvío | No hay dominio todavía. Queda como plan B si la regla de Render no deja pasar POST o cookies |
| Seguir con la sesión en memoria | Ningún cambio | Volver a ingresar en cada recarga no sirve para el uso real desde el 6/11 |

## Consecuencias

**Positivas**
- La sesión sobrevive recargas y el cierre de la app; ningún script puede leer el refresh token.
- La API queda en la misma dirección que cada sitio: CORS deja de ser necesario para los sitios desplegados.

**Negativas o costo que aceptamos**
- Cada llamada a la API pasa por el reenvío de Render: un salto más.
- Hasta el despliegue del jueves 29 no está confirmado que la regla deje pasar POST y `Set-Cookie`. Si no, se pasa al plan B (dominio propio).
- Un celular perdido conserva la sesión hasta 30 días: hay que darlo de baja desde Usuarios (E01-02, criterio 4, ya corta todas sus sesiones).

**Qué se vuelve más difícil de ahora en adelante**
- Cambiar la ruta `/api` o el nombre de los servicios exige tocar la regla de Render, `VITE_API_URL` y la ruta de la cookie a la vez.

## Impacto en las reglas del repositorio

- [ ] [`CLAUDE.md`](../../../CLAUDE.md): reglas o estructura
- [ ] [`docs/code-standards.md`](../../code-standards.md)
- [ ] `ALLOWED_TOPLEVEL` en `.claude/hooks/guard_edit.py` (carpeta nueva en la raíz)
- [ ] `.github/workflows/ci.yml`
- [x] `.env.example`: variables de la cookie (en la PR del backend)
- [x] Historias afectadas en `docs/stories/`: nueva E01-07; E01-02 deja de decir que persistir la sesión queda para después
- [ ] Ninguno

## Referencias

- [E01-02](../../stories/E01-acceso/E01-02-mantener-y-cerrar-la-sesion.md) y [E01-07](../../stories/E01-acceso/E01-07-mantener-la-sesion-al-recargar-o-reabrir.md).
- [ADR 0004](0004-hosting-paas-postgres-administrado.md) (hosting), [ADR 0006](0006-visibilidad-por-rol-en-la-api.md) (visibilidad por rol).
- `render.yaml` y [despliegue](../../workflow/despliegue.md).
- Render, reglas de redirección y reenvío: <https://render.com/docs/redirects-rewrites>.
