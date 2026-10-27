---
id: E05-04
title: "Cerrar una orden con falla y reparación de listas"
epic: E05
phase: 1
priority: must
status: done
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E05-03, E02-03, E02-04, E02-09, E02-10]
blocked_by: []
assumes: []
---

# E05-04 Cerrar una orden con falla y reparación de listas

## Historia

**Como** escuadrilla, **quiero** cerrar una orden eligiendo de listas quiénes fueron, qué tareas se hicieron, la falla, la reparación y cómo quedó el equipo, **para** cerrar rápido, casi sin escribir, y dejar datos medibles.

## Criterios de aceptación

1. **Dado:** una orden `En curso` de mi escuadrilla. **Cuando:** abro su detalle. **Entonces:** veo el botón "Cerrar orden", que abre el formulario de cierre.
2. **Dado:** el formulario. **Cuando:** lo completo. **Entonces:** tildo quiénes fueron de la lista de técnicos activos (al menos uno, E02-09).
3. **Dado:** las tareas del tipo de trabajo. **Cuando:** cierro. **Entonces:** tildo las que se hicieron; se puede cerrar aunque falte alguna y queda registrado cuáles se tildaron.
4. **Dado:** un tipo de trabajo que pide falla y reparación (E02-10) y el resultado "Resuelta" (E05-08). **Cuando:** cierro. **Entonces:** elijo la falla y después la reparación, de listas y no como texto libre. Las dos son obligatorias. En los demás casos se pueden cargar pero no se exigen.
5. **Dado:** la lista de fallas. **Cuando:** se muestra. **Entonces:** tiene las fallas activas del tipo de equipo de la orden y las genéricas; si la orden no tiene equipo, solo las genéricas. Las reparaciones son las activas de la falla elegida, con el mismo criterio de tipo de equipo.
6. **Dado:** la lista de fallas o de reparaciones. **Cuando:** elijo "Otro". **Entonces:** escribo cuál, y la observación pasa a ser obligatoria.
7. **Dado:** el formulario. **Cuando:** indico cómo quedó el equipo. **Entonces:** elijo "Funcionando bien", "Funciona con observaciones" o "No funciona". Con observaciones, la observación es obligatoria. Se pide salvo con el resultado "No se pudo hacer" (E05-08).
8. **Dado:** un cierre incompleto. **Cuando:** intento enviarlo. **Entonces:** se marca qué falta, en la app y en la API (422 con el campo).
9. **Dado:** las listas y la respuesta del cierre. **Cuando:** se inspeccionan. **Entonces:** no incluyen precios, mano de obra ni datos de otros clientes.
10. **Dado:** una orden que no es `En curso` de mi escuadrilla. **Cuando:** intento cerrarla. **Entonces:** recibo 404, como en E05-02.

## Fuera de alcance

- El resultado y su efecto en la orden: E05-08 (se envían juntos).
- Reintentos y doble envío: E05-12.
- Repuestos (E05-05), foto (E05-06) y firma (E05-07): se suman al cierre cuando estén precios y stock (E02-06, E08) y el bucket (E00-09).
- Borrador en el celular si se corta la señal: E05-13.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26, con el prototipo del cliente:

- **Tareas tildadas sin exigirlas**: el prototipo exige todas para cerrar como hecha; acá se registran las tildadas y no se traba el cierre.
- **Falla y reparación según el tipo de trabajo**: administración marca qué tipos las piden (E02-10). Responde la pregunta de instalación y relevamiento.
- **Cómo quedó el equipo, en tres opciones**, aparte del resultado, como en el prototipo.
- **Cierre básico primero**: repuestos, foto y firma se agregan después, sin cambiar lo de esta historia.

## Notas técnicas

- Cada reparación pertenece a una falla (decidido al refinar E02-04). "Otro" es una opción fija del cierre, no un valor del catálogo: se guarda en `failure_other_text` o `repair_other_text`.
- Listas para el técnico: `GET /tech/orders/{id}/closure-options` devuelve técnicos activos, tareas activas del tipo de trabajo, si pide falla y reparación, y las fallas con sus reparaciones según el tipo de equipo de la orden. Esquemas `*TechnicianOut`, solo nombres e ids.
- El cierre se envía en un solo `POST /tech/orders/{id}/closure` con la clave de idempotencia de E05-12 y el resultado de E05-08. Tablas `work_order_closure`, `work_order_closure_technician` y `work_order_closure_task` (ver `data-model.dbml`).
- Que la falla y la reparación no exigidas por el resultado sean opcionales es una propuesta del refinamiento: si negocio prefiere exigirlas también en "Requiere otra visita", es un cambio de validación.

## Notas de implementación

Se entrega junto con E05-04, E05-08 y E05-12, en PR separados: backend, listado de pendientes (web-admin) y formulario en la PWA.

- Backend (PR 1): migración `b7d2e9f4c613` con `work_order_closure`, `work_order_closure_technician`, `work_order_closure_task` y los enums `closure_outcome` (ya con `needs_pickup` para E06-02), `equipment_condition` y `not_done_reason`. El `stage_id` del modelo llega con las etapas de taller (E06).
- `GET /tech/orders/{id}/closure-options`: técnicos activos, tareas activas con id, si el tipo pide falla y reparación, y las fallas activas con sus reparaciones (genéricas y, si la orden tiene equipo, las de su tipo).
- `POST /tech/orders/{id}/closure` (`app/services/closures.py`): valida en orden fijo (lo cargado primero, lo que falta después) y responde 422 con `code`, `message` y `field`. Cierre, transición (`close_done` o `request_revisit`), fin de la asignación y evento en una transacción. 201 al cerrar y 200 al reenviar con la misma clave; una clave usada en otra orden, 422 `idempotency_key_reused`. Una orden que no está En curso de la escuadrilla, 404.
- Con datos reales: "No enciende" es genérica pero todas sus reparaciones son de un tipo de equipo; sin equipo en la orden, la reparación solo puede ser "Otro".
- PWA (PR 3): en el detalle de una orden `En curso`, botón "Cerrar orden" que lleva a `/ordenes/{id}/cerrar`. Pantalla aparte del detalle (el prototipo lo tiene debajo) para que el botón atrás del celular funcione bien. Tarjetas numeradas como en el prototipo: quiénes fueron, tareas, resultado, falla, reparación, cómo quedó el equipo y observación.
- El resultado va antes que la falla y el equipo (en el prototipo, después): es el que decide qué se pide. Las reparaciones son las de la falla elegida; cambiar la falla borra la reparación. "Otro" abre un campo de texto. Falla y reparación dicen "(obligatoria)" u "(opcional)" según el tipo de trabajo y el resultado.
- Las reglas de qué falta están en `pwa-tecnico/src/features/orders/closure.ts`, iguales a las de `services/closures.py`. El botón queda siempre habilitado (el prototipo lo deshabilita): al tocarlo marca cada campo que falta, lista los faltantes arriba del botón y lleva la pantalla al primero. Un 422 de la API marca el mismo campo con su mensaje.
- Al cerrar vuelve a la lista con el aviso "Orden N° X cerrada." o "devuelta a la oficina.". Un 404 muestra que la orden ya no está en curso para la escuadrilla.
- Probado en el navegador contra el backend real con los tres resultados: faltantes marcados, reparaciones filtradas por falla, "Otro" con observación, el cierre guardado en la base y el aviso en pendientes del web-admin.
