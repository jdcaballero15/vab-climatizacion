# ADR 0007: Orden de trabajo unificada con etapas

**Estado:** Aceptado

## Contexto

Hoy cada equipo que se retira genera tres órdenes separadas (retiro, taller y devolución). Eso rompe el historial y obliga a facturar tres veces.

## Decisión

Una orden de trabajo tiene `kind` (`on_site` o `workshop`) y, cuando es de taller, una secuencia de **etapas** (`work_order_stage`): `pickup`, `workshop`, `delivery`.

- Cada etapa tiene su propia asignación, por lo que puede hacerla un técnico distinto.
- `pickup` y `delivery` requieren firma del cliente (nombre y DNI).
- La orden se factura una sola vez, al terminar la última etapa.
- Una orden en el lugar puede convertirse en orden de taller cuando el técnico marca "requiere retiro". Se conserva el trabajo ya registrado y se agregan las etapas.
- En todo momento se puede listar qué equipos están en el galpón y en qué etapa.

## Consecuencias

- El estado de la orden (ver [máquina de estados](../order-state-machine.md)) se calcula a partir del avance de sus etapas.
- El modelo de datos tiene `work_order_stage` y `work_order_assignment` con referencia opcional a la etapa.
- El comprobante PDF de retiro y de devolución se genera por etapa.

## Nota del 2026-11-03: etapas en fila (opción A)

Para el arranque del 2026-11-06, Gonza eligió una versión más simple que la de arriba:

- Las etapas van **en fila** y la orden tiene **una sola asignación vigente** a la vez, la de la etapa que toca. No hay tabla `work_order_stage`: la orden guarda su etapa en `work_order.workshop_stage` y cada cierre, la que cerró (`work_order_closure.workshop_stage`).
- Al cerrar el retiro o el galpón, la orden **vuelve a Pendiente** con la etapa siguiente y la oficina la asigna como cualquier otra (acción `complete_stage`). Al cerrar la devolución queda `Terminada`. Asignar, reasignar, cancelar y devolver a la escuadrilla funcionan igual que en una orden en el lugar.
- Retiro y devolución se firman con **firma y nombre, sin DNI**. El galpón no se firma.
- Las etapas en paralelo (asignar las tres de una vez, orden `En curso` de punta a punta) quedan para más adelante, si hacen falta.
