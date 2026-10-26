---
id: E05-13
title: "No perder un cierre si se corta la conexión"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: M
areas: [pwa]
depends_on: [E05-04, E05-12]
blocked_by: []
assumes: []
---

# E05-13 No perder un cierre si se corta la conexión

## Historia

**Como** técnico, **quiero** que lo que cargué en un cierre quede guardado en el celular si se corta la señal, **para** no tener que volver a cargarlo ni pedirle de nuevo la firma al cliente.

## Criterios de aceptación

1. **Dado:** un técnico cargando un cierre. **Cuando:** completa datos (falla, reparación, repuestos, observación, fotos, firma). **Entonces:** quedan guardados en el celular como borrador de esa orden.
2. **Dado:** un borrador. **Cuando:** el técnico cierra la app o se apaga el celular y la vuelve a abrir. **Entonces:** el borrador sigue intacto.
3. **Dado:** el celular sin conexión. **Cuando:** el técnico toca "Enviar". **Entonces:** la app avisa que el cierre quedó pendiente y lo envía solo cuando vuelve la señal.
4. **Dado:** un envío que se corta a mitad. **Cuando:** se reintenta y el servidor ya lo había recibido. **Entonces:** no se duplica el cierre (clave de idempotencia de E05-12).
5. **Dado:** un cierre enviado con éxito. **Cuando:** el servidor lo confirma. **Entonces:** el borrador se borra del celular.
6. **Dado:** lo guardado en el celular. **Cuando:** se inspecciona. **Entonces:** no contiene precios, mano de obra ni historial del cliente.
7. **Dado:** un técnico con un cierre pendiente de enviar. **Cuando:** cierra sesión. **Entonces:** la app le avisa antes y no borra el borrador sin su confirmación.

## Notas técnicas

- Ver ADR 0009. El borrador se guarda en IndexedDB, una entrada por orden, con la clave de idempotencia generada al empezar el cierre.
- Fotos y firma se guardan en el celular hasta que se suben al bucket con URL firmada (E00-09).
- Cubre el criterio 3 de E01-02 (aviso al cerrar sesión), que quedó diferido por `D-001`.

## Preguntas abiertas

- Si mientras el cierre estaba pendiente la oficina reasignó o canceló la orden, el servidor rechaza el cierre. ¿Alcanza con que la app muestre el motivo y conserve el borrador para que el técnico avise a la oficina, o hace falta un circuito de revisión como el de E99-08 (icebox)?

## Fuera de alcance

- Ver órdenes o trabajar sin señal (E99-06).
- Cola de varios cierres y pantalla de sincronización (E99-07 y E99-08).
