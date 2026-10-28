---
id: E05-07
title: "Firma del cliente en pantalla con su nombre"
epic: E05
phase: 1
priority: must
status: in_progress
roles: [technician, admin]
size: M
areas: [backend, pwa, web-admin]
depends_on: [E05-04, E00-09, E05-13]
blocked_by: []
assumes: []
---

# E05-07 Firma del cliente en pantalla con su nombre

## Historia

**Como** técnico, **quiero** que el cliente firme en la pantalla y quede su nombre, **para** tener constancia de que el trabajo fue recibido.

## Criterios de aceptación

1. **Dado:** un cierre. **Cuando:** el cliente firma con el dedo en la pantalla y se escribe su nombre (aclaración). **Entonces:** al enviar, la imagen de la firma se sube al bucket (E00-09) y el cierre guarda la firma con el nombre y la hora.
2. **Dado:** un cierre sin firma. **Cuando:** se intenta enviar. **Entonces:** la app pide la firma o el motivo por el que no hay: "Cliente ausente", "No quiso firmar" u "Otro" (con texto obligatorio). Sin una de las dos no se envía, y la API lo rechaza igual (422, campo `signature`). Vale para cualquier resultado del cierre (`D-011`).
3. **Dado:** una firma sin nombre. **Cuando:** se intenta enviar. **Entonces:** se marca que falta el nombre de quien firma.
4. **Dado:** el resultado "No se pudo hacer" con "Cliente ausente o sin acceso". **Cuando:** se llega a la firma. **Entonces:** el motivo "Cliente ausente" ya viene elegido, y se puede cambiar.
5. **Dado:** una firma trazada. **Cuando:** se gira el celular, se vuelve atrás, se recarga la app o se corta la señal. **Entonces:** la firma no se pierde: viaja en el borrador del celular hasta enviarse (E05-13). "Borrar" la limpia para firmar de nuevo.
6. **Dado:** una orden Terminada. **Cuando:** la administración la revisa (E04-08). **Entonces:** ve la firma con el nombre y la hora, o el motivo por el que no hay firma. La imagen se sirve con URL firmada de corta duración.
7. **Dado:** el técnico. **Cuando:** pide la lista o el detalle de sus órdenes. **Entonces:** no recibe firmas de cierres anteriores (no ve historial).
8. **Dado:** el nombre de quien firma. **Cuando:** se procesa el cierre. **Entonces:** no aparece en logs.

## Fuera de alcance

- DNI de quien firma: no se pide (`D-008`, Gonza 2026-10-28).
- Firma en retiro y devolución del taller (E06-04 y E06-06).
- Comprobante en PDF o por mail con la firma (E09).
- Retención de firmas y aviso legal (`D-008`, E12-04).

## Notas técnicas

- Backend: tabla `signature` del modelo de datos, con `closure_id`, `purpose` `closure`, `signer_name`, `image_file_id` (único) y `signed_at`, sin `signer_dni`. El motivo sin firma va en `work_order_closure`: enum `no_signature_reason` (`client_absent`, `refused`, `other`) y `no_signature_text` (solo y obligatorio con `other`). El servicio exige exactamente una de las dos cosas. Migración reversible; los cierres anteriores quedan sin firma ni motivo.
- `ClosureCreate` suma `signature` (`file_id` y `signer_name`) o `no_signature_reason` con su texto. La imagen sigue las reglas de las fotos de E05-06: subida por el mismo usuario, confirmada y sin usar en otro cierre. Propósito de archivo nuevo `closure_signature`, solo `image/png`.
- PWA: lienzo con eventos de puntero (dedo, lápiz o mouse) que exporta un PNG chico. El trazo se guarda como `Blob` en el borrador de E05-13 junto con el nombre o el motivo, y se sube con las fotos antes de mandar el cierre (`closureSender`). Se agregan los campos al copiado de `closureDrafts.ts` (criterio 8 de E05-13).
- Web-admin: la firma en el detalle de la orden terminada, con la misma URL firmada que las fotos.
- Hecho en el backend (PR 1): migración `d1a4f7c2e958`, modelo `Signature`, enums `no_signature_reason` y `signature_purpose`, CHECK del texto con "Otro". Errores con campo: `signature` (`signature_required`, `signature_ambiguous`, `signature_not_available`, `signature_already_used`), `signer_name` (`signer_name_required`) y `no_signature_text` (`no_signature_text_required`, `no_signature_text_not_allowed`). `GET /admin/orders/{id}/closure` suma `signature` (nombre, hora y URL firmada), `no_signature_reason` y `no_signature_text`.
- Hecho en la PWA (PR 2): `SignaturePad` (lienzo de 600x240 con eventos de puntero, estirado por CSS, así girar el celular no cambia el trazo; exporta PNG al terminar cada trazo). El trazo va en `StoredClosure.signature` y el nombre o el motivo en el borrador; los borradores guardados antes vuelven sin firma ni motivo. `closureSender` sube la firma después de las fotos con `uploadOne(..., SIGNATURE)` y no la resube si ya llegó; un 422 en `signature` la deja para subir de nuevo. Con un motivo elegido el trazo queda en el celular pero no se manda. "Cliente ausente o sin acceso" preelige "Cliente ausente" si no hay firma ni motivo.

## Preguntas abiertas

- ¿El retiro y la devolución del taller (E06-04, E06-06 y sus comprobantes E09-01 y E09-02) también van sin DNI? Esas historias lo piden; no se cambian acá.
