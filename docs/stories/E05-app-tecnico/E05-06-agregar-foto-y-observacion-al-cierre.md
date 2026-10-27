---
id: E05-06
title: "Agregar foto y observación al cierre"
epic: E05
phase: 1
priority: must
status: ready
roles: [technician, admin]
size: M
areas: [backend, pwa, web-admin]
depends_on: [E05-04, E00-09]
blocked_by: []
assumes: []
---

# E05-06 Agregar foto y observación al cierre

## Historia

**Como** técnico, **quiero** adjuntar fotos y escribir una observación al cerrar, **para** dejar evidencia del trabajo y aclaraciones.

## Criterios de aceptación

1. **Dado:** un cierre en curso. **Cuando:** saco una foto con la cámara o elijo una de la galería. **Entonces:** se comprime en el celular, se ve en miniatura en el formulario y se puede quitar antes de enviar.
2. **Dado:** un cierre. **Cuando:** intento agregar una sexta foto. **Entonces:** la app no lo permite y avisa que el máximo es 5. Las fotos son opcionales en cualquier resultado del cierre.
3. **Dado:** un cierre con fotos. **Cuando:** se envía. **Entonces:** cada foto se sube al bucket con URL firmada (E00-09) y el cierre queda asociado a esas fotos; la base guarda solo clave, tipo y tamaño.
4. **Dado:** un cierre que referencia una foto que no subió el mismo usuario, que no está confirmada o que ya usa otro cierre. **Cuando:** se envía. **Entonces:** se rechaza (422, campo `photo_ids`).
5. **Dado:** una subida que falla por mala señal. **Cuando:** se reintenta. **Entonces:** no se pierde la foto ni se duplica en el cierre (el reintento completo lo cubre E05-13).
6. **Dado:** una orden Terminada con fotos. **Cuando:** la administración la revisa (E04-08). **Entonces:** ve las fotos (miniatura y abrirla grande) con URLs firmadas de corta duración.
7. **Dado:** el técnico. **Cuando:** pide la lista o el detalle de sus órdenes. **Entonces:** no recibe fotos de cierres anteriores (no ve historial).
8. **Dado:** la observación. **Cuando:** la escribo. **Entonces:** sigue la regla de E05-04: opcional, salvo los casos que ya la piden (por ejemplo "Otro").

## Fuera de alcance

- Comentario por foto, dibujar sobre la foto o pedir una foto "antes" y otra "después".
- Fotos obligatorias por tipo de trabajo.
- Borrar fotos subidas y no usadas (E00-11).

## Notas técnicas

- Compresión en el navegador con `canvas` (lado mayor 1600 px, JPEG calidad 0,8). Sin dependencias nuevas. Entrada con `<input type="file" accept="image/*" capture="environment">` y otra sin `capture` para la galería.
- `ClosureCreate` suma `photo_ids: list[uuid] = []` (máximo 5). Tabla `work_order_closure_photo` (`closure_id`, `file_id`, `position`), con `file_id` único. Migración reversible.
- Orden de envío: subir cada foto (pedir subida, `PUT`, confirmar) y después el `POST` del cierre con los ids. Con la idempotencia de E05-12, reenviar el cierre con las mismas fotos no duplica nada.
- `ClosureAdminOut` suma las fotos con URL firmada de descarga (5 minutos). `ClosureTechnicianOut` no las devuelve.
- Medición fuera de rango como motivo para exigir observación queda para E07-07 (todavía no hay mediciones).
