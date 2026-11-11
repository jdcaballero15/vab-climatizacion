---
id: E12-06
title: "Uso cómodo de la app del técnico a la intemperie"
epic: E12
phase: 1
priority: should
status: done
roles: [technician]
size: M
areas: [pwa]
depends_on: [E00-03]
blocked_by: []
assumes: []
---

# E12-06 Uso cómodo de la app del técnico a la intemperie

## Historia

**Como** técnico, **quiero** que la app se pueda usar con una mano, con sol y con guantes finos, **para** trabajar rápido en campo.

## Criterios de aceptación

1. **Dado:** las pantallas del técnico. **Cuando:** se revisan. **Entonces:** los botones tienen al menos 48 px de alto y espacio entre sí.
2. **Dado:** el contraste. **Cuando:** se mide. **Entonces:** cumple WCAG AA.
3. **Dado:** la app. **Cuando:** se usa en un celular Android de gama baja. **Entonces:** responde sin demoras notorias.
4. **Dado:** el texto. **Cuando:** el celular tiene la fuente agrandada. **Entonces:** la interfaz sigue siendo usable.

## Hecho

- PWA: pestañas y link al mapa a 48 px; `--text-muted` más oscuro para contraste AA sobre blanco y sobre el fondo.
- `src/test/outdoorUse.test.ts` controla el alto de lo que se toca, el contraste AA de los colores de texto y que las letras vayan en rem (siguen la fuente agrandada del celular).
- El criterio 3 (gama baja) se verifica a mano en un celular de la escuadrilla.
