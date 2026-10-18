---
id: E00-02
title: "Base de la app de administración"
epic: E00
phase: 1
priority: must
status: done
roles: [dev]
size: S
areas: [web-admin, infra]
depends_on: []
blocked_by: []
assumes: []
---

# E00-02 Base de la app de administración

## Historia

**Como** equipo de desarrollo, **quiero** el esqueleto de `web-admin` con React, TypeScript y Vite, con lint, tests y build en CI, **para** empezar a construir pantallas de administración sobre una base común.

## Criterios de aceptación

1. **Dado:** el repositorio recién clonado. **Cuando:** corro `npm ci && npm run build` en `web-admin`. **Entonces:** compila sin errores.
2. **Dado:** un cambio en `web-admin`. **Cuando:** se abre un PR. **Entonces:** CI corre lint, typecheck, tests y build.
3. **Dado:** la API del backend. **Cuando:** se genera el cliente tipado desde OpenAPI. **Entonces:** el frontend usa los tipos generados y no tipos escritos a mano.
4. **Dado:** la app corriendo. **Cuando:** abro la ruta raíz. **Entonces:** veo una pantalla de inicio de sesión vacía en español.

## Notas técnicas

- Incluir `package-lock.json` para que el job de CI deje de omitirse.
- TanStack Query para datos del servidor. Estructura por funcionalidad, no por tipo de archivo.

## Notas de implementación

- Esqueleto Vite + React 18 + TypeScript estricto en `web-admin/`. Scripts: `lint` (ESLint 9 flat), `typecheck` (`tsc -b`), `test` (Vitest + Testing Library), `build` (`tsc -b && vite build`), más `format` (Prettier) y `generate:api`. Son los que corre el job `web-admin` del CI; se incluye `package-lock.json`.
- Cliente de API tipado desde el OpenAPI del backend (criterio 3): `web-admin/openapi.json` es el snapshot del esquema (`app.openapi()`), `npm run generate:api` genera `src/api/schema.d.ts` con `openapi-typescript`, y `src/api/client.ts` usa esos tipos con `openapi-fetch`. No hay tipos escritos a mano; el `.d.ts` generado se excluye de lint y Prettier.
- Estructura por funcionalidad: `src/features/auth/LoginPage.tsx` (login vacío en español en la ruta raíz, criterio 4), `src/app/` (router y QueryClient de TanStack Query).
- Verificado: `npm ci && npm run build` compila; lint, typecheck y 2 tests en verde; captura del login confirmada.
- El snapshot del OpenAPI hoy solo tiene `/health`; se regenera con `generate:api` a medida que crece la API.
