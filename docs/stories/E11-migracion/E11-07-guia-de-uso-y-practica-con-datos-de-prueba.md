---
id: E11-07
title: "Guía de uso y práctica con datos de prueba"
epic: E11
phase: 1
priority: must
status: ready
roles: [admin, technician]
size: M
areas: [datos]
depends_on: [E11-09]
blocked_by: []
assumes: []
---

# E11-07 Guía de uso y práctica con datos de prueba

## Historia

**Como** administración y escuadrillas, **quiero** una guía corta de lo que hace cada uno y una forma de practicar sin ensuciar el trabajo real, **para** arrancar a usar el sistema el 2026-11-06 sin depender de que alguien nos explique.

## Criterios de aceptación

1. **Dado:** el sistema en producción. **Cuando:** la oficina y las escuadrillas practican. **Entonces:** usan el cliente ficticio "PRÁCTICA - no facturar" y, al terminar, cancelan esas órdenes con el motivo "Otro" y el texto "Práctica". La guía de la oficina explica cómo.
2. **Dado:** la guía de la oficina. **Cuando:** se entrega. **Entonces:** cubre entrar y cambiar la contraseña, crear una orden (cliente, domicilio, equipo, tipo, canal), asignar, reasignar, reprogramar, desasignar, cambiar el equipo, cancelar, seguir las abiertas, ver las terminadas con su cierre, fotos y firma, las que volvieron a Pendientes, y administrar usuarios, escuadrillas, técnicos de campo y catálogos.
3. **Dado:** la guía de la escuadrilla. **Cuando:** se entrega. **Entonces:** cubre entrar, dejar la app en la pantalla de inicio, "Para hacer" y "Hechas esta semana", abrir e iniciar una orden, cerrarla (quiénes fueron, tareas, resultado, falla y reparación, estado del equipo, fotos y firma o motivo) y qué pasa si se corta la señal o se cierra la app, en pasos cortos con capturas.
4. **Dado:** las capturas de las guías. **Cuando:** se revisan. **Entonces:** no muestran datos reales: salen del entorno local con datos ficticios.

## Fuera de alcance

- Facturar, cobrar, repuestos y stock: todavía no existen (E04-09, E04-10, E05-05, E08). Se suman a la guía cuando se implementen.
- Un entorno de práctica aparte: se decidió practicar en producción con el cliente ficticio (Gonza, 2026-10-29).
- Recuperar la contraseña por correo: la restablece la oficina (E01-05).

## Notas técnicas

- Formato: dos docs con link (uno para la oficina y otro para las escuadrillas), como el guion de la prueba del 2026-10-30. Se pueden compartir por separado, imprimir o exportar a PDF. No van en el repositorio.
- Capturas del entorno local (skill `run-local`) con datos ficticios: usuarios de `make seed`, clientes y órdenes inventados.
- Textos de la interfaz tal como aparecen en pantalla. Si un botón cambia de nombre, se corrige la guía.
- Cuando entre facturación (E04-09), las órdenes del cliente "PRÁCTICA - no facturar" no tienen que aparecer como pendientes de facturar: anotarlo al refinar esa historia.
