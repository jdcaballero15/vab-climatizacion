# web-admin

App de administración y tablero. Uso principal en PC o tablet, con el tablero también usable desde el celular (dirección).

**Estado: esqueleto creado** en la historia [E00-02](../docs/stories/E00-fundaciones/E00-02-base-de-la-app-de-administracion.md).

## Comandos

```bash
npm ci               # instala dependencias
npm run dev          # servidor de desarrollo
npm run build        # typecheck y build de produccion
npm run lint         # ESLint
npm run typecheck    # tsc -b
npm test             # Vitest
npm run generate:api # regenera src/api/schema.d.ts desde openapi.json
```

El cliente de API (`src/api/`) se genera desde el OpenAPI del backend: `openapi.json` es el snapshot del esquema y `generate:api` produce los tipos. No se escriben tipos a mano.

## Stack previsto

- React 18 y TypeScript estricto, Vite.
- TanStack Query para datos del servidor. Cliente de API generado desde el OpenAPI del backend.
- Estructura por funcionalidad (`src/features/orders`, `src/features/catalogs`, etc.), no por tipo de archivo.
- ESLint, Prettier, Vitest y Testing Library.

## Pantallas (por épica)

| Épica | Pantallas |
|---|---|
| E04 | Panel de órdenes, alta de orden, detalle con línea de tiempo, revisión, facturación y cobro |
| E03 | Clientes, equipos, fichas con historial |
| E02 | Catálogos y precios |
| E06 | Equipos en el galpón |
| E07 | Plantillas de checklist, abonos, aprobación en bloque |
| E08 | Stock, transferencias, movimientos |
| E10 | Tablero |
| E01 y E12 | Usuarios y auditoría |

## Reglas

- Interfaz en español, densa y eficiente para escritorio.
- Acciones sensibles con confirmación.
- Sin datos reales en capturas ni fixtures.
- Seguir `CLAUDE.md` y el agente `frontend-dev`.
