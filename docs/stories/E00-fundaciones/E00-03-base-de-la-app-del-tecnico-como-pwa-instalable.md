---
id: E00-03
title: "Base de la app del técnico como PWA instalable"
epic: E00
phase: 1
priority: must
status: done
roles: [dev]
size: M
areas: [pwa, infra]
depends_on: []
blocked_by: []
assumes: []
---

# E00-03 Base de la app del técnico como PWA instalable

## Historia

**Como** equipo de desarrollo, **quiero** el esqueleto de `pwa-tecnico` como PWA instalable en Android, **para** entregar al técnico una app sin pasar por tiendas de aplicaciones.

## Criterios de aceptación

1. **Dado:** la app publicada en staging. **Cuando:** la abro en Chrome de Android. **Entonces:** puedo instalarla en la pantalla de inicio y abre a pantalla completa.
2. **Dado:** la app instalada. **Cuando:** abro sin conexión. **Entonces:** carga la carcasa de la aplicación desde el service worker.
3. **Dado:** una nueva versión desplegada. **Cuando:** el técnico abre la app con conexión. **Entonces:** se actualiza sin reinstalar y se le avisa si hay cambios pendientes de aplicar.
4. **Dado:** un cambio en `pwa-tecnico`. **Cuando:** se abre un PR. **Entonces:** CI corre lint, typecheck, tests y build.

## Notas técnicas

- La carcasa offline no depende de `D-001`: instalarse y abrir sin red es útil en cualquier caso. El almacenamiento de datos offline está en E05-09 a E05-11.

## Notas de implementación

- Esqueleto Vite + React 18 + TypeScript estricto en `pwa-tecnico/`, con el mismo stack base que `web-admin` (ESLint, Prettier, Vitest + Testing Library, TanStack Query, react-router, cliente de API tipado desde el OpenAPI). Scripts `lint`, `typecheck`, `test`, `build` + `package-lock.json` para activar el job de CI (criterio 4).
- PWA con `vite-plugin-pwa` (`registerType: "prompt"`): genera el manifest (`display: standalone`, íconos 192/512 y maskable, `lang: es`, `theme_color`) para instalarse en Android (criterio 1) y un service worker Workbox que precachea el app shell con `navigateFallback` para abrir sin conexión (criterio 2). Íconos placeholder en `public/`.
- Aviso de actualización (criterio 3): `src/pwa/useAppUpdate.ts` envuelve `useRegisterSW`; `UpdateBanner` (presentacional, con test) avisa y aplica la versión nueva sin reinstalar; `PwaUpdater` los conecta.
- Shell inicial: `features/auth/LoginPage.tsx` (login en español, botones de 48px). Verificado: lint, typecheck y 3 tests en verde, `build` genera `sw.js` + `manifest.webmanifest`, captura del shell confirmada.
- Alcance: los criterios 1 y 2 (instalación real y apertura offline en Chrome de Android) se validan de punta a punta sobre staging con HTTPS (E00-05). Acá queda verificado que el manifest y el service worker se generan correctamente.
