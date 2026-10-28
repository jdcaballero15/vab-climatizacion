---
id: E05-13
title: "No perder un cierre si se corta la conexión"
epic: E05
phase: 1
priority: must
status: in_progress
roles: [technician]
size: M
areas: [pwa]
depends_on: [E05-04, E05-12, E05-06]
blocked_by: []
assumes: []
---

# E05-13 No perder un cierre si se corta la conexión

## Historia

**Como** técnico, **quiero** que lo que cargué en un cierre quede guardado en el celular si se corta la señal, **para** no tener que volver a cargarlo ni pedirle de nuevo la firma al cliente.

## Criterios de aceptación

1. **Dado:** un técnico cargando un cierre. **Cuando:** completa datos (resultado, técnicos, tareas, falla, reparación, estado del equipo, motivo, observación, fotos y, cuando exista, firma). **Entonces:** quedan guardados en el celular como borrador de esa orden, sin tener que tocar ningún botón.
2. **Dado:** un borrador. **Cuando:** el técnico cierra la app, recarga o se apaga el celular y la vuelve a abrir. **Entonces:** al entrar al cierre de esa orden el borrador sigue intacto, y en la lista la orden muestra "Borrador" o "Pendiente de enviar".
3. **Dado:** el celular sin conexión. **Cuando:** el técnico toca "Enviar". **Entonces:** la app avisa que el cierre quedó pendiente y lo envía sola cuando vuelve la señal (o al volver a abrir la app con señal), sin que el técnico tenga que repetir nada.
4. **Dado:** un envío que se corta a mitad (fotos subidas o no, cierre recibido o no). **Cuando:** se reintenta. **Entonces:** no se duplica el cierre ni las fotos (clave de idempotencia de E05-12 y fotos ya confirmadas que no se vuelven a subir).
5. **Dado:** un cierre enviado con éxito. **Cuando:** el servidor lo confirma. **Entonces:** el borrador y sus fotos se borran del celular.
6. **Dado:** un cierre pendiente que el servidor rechaza porque la oficina canceló o reasignó la orden (404 o 409). **Cuando:** llega la respuesta. **Entonces:** la app muestra por qué, **no borra el borrador** y lo deja marcado como "Rechazado: avisale a la oficina", con un botón para descartarlo (con confirmación).
7. **Dado:** un cierre pendiente rechazado por un error de validación (422). **Cuando:** llega la respuesta. **Entonces:** la app vuelve al formulario con el borrador y marca el campo con el error.
8. **Dado:** lo guardado en el celular. **Cuando:** se inspecciona. **Entonces:** no contiene precios, mano de obra ni historial del cliente.
9. **Dado:** un técnico con un borrador o un cierre pendiente. **Cuando:** cierra sesión. **Entonces:** la app le avisa antes y no lo borra sin su confirmación.

## Fuera de alcance

- Ver órdenes o trabajar sin señal (E99-06).
- Cola de varios cierres y pantalla de sincronización (E99-07 y E99-08). Puede haber un borrador por orden, pero no hay pantalla que los liste.
- Guardar en el servidor el cierre rechazado como intento para que la oficina lo vea (ver preguntas abiertas).
- Envío en segundo plano con la app cerrada (Background Sync): el reintento ocurre con la app abierta.

## Notas técnicas

- Ver ADR 0009. El borrador se guarda en IndexedDB, una entrada por orden, con la clave de idempotencia generada al empezar el cierre. Las fotos se guardan como `Blob` ya comprimidas, con el id de archivo una vez confirmada la subida. Sin dependencias nuevas, salvo que el PR justifique un envoltorio chico de IndexedDB.
- El reintento escucha el evento `online`, corre al abrir la app y reintenta con espera creciente mientras la app está abierta.
- Un borrador es de la sesión de la escuadrilla: si entra otro usuario en el mismo celular, no ve borradores ajenos (clave por usuario).
- Cubre el criterio 3 de E01-02 (aviso al cerrar sesión), que quedó diferido por `D-001`.
- Primera parte (criterios 1, 2, 8 y 9): `pwa-tecnico/src/features/orders/closureDrafts.ts`, módulo propio sobre IndexedDB (base `vab-ot`, almacén `closure-drafts`, clave `[userId, orderId]`). Copia campo por campo lo que carga el técnico, así no se cuela otro dato. Las operaciones van en fila para que un guardado viejo no pise uno nuevo ni el borrado. Al restaurar, lo que la oficina sacó de las listas vuelve a sin elegir (`restoreDraft`). Al cerrar sesión el borrador no se borra: queda para cuando vuelva a entrar el mismo usuario. `fake-indexeddb` solo para los tests.

## Preguntas abiertas

- **Cierre rechazado como intento.** Negocio respondió (2026-10-27, refinamiento de E04-07) que no se pierde nada de lo cargado y queda registrado como intento. Esta historia cubre la primera mitad (nada se pierde en el celular hasta que el técnico lo descarta). Que el servidor guarde el intento y la oficina lo vea en la orden va en una historia aparte, después del 6/11, junto con E04-06 (detalle con línea de tiempo).
