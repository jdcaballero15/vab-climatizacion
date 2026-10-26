---
id: E05-03
title: "Iniciar una orden"
epic: E05
phase: 1
priority: must
status: ready
roles: [technician]
size: S
areas: [backend, pwa]
depends_on: [E05-02, E04-01]
blocked_by: []
assumes: []
---

# E05-03 Iniciar una orden

## Historia

**Como** escuadrilla, **quiero** marcar que empezamos una orden, **para** que administración sepa en cuál estamos trabajando.

## Criterios de aceptación

1. **Dado:** una orden `Asignada` a mi escuadrilla, abierta en el detalle (E05-02). **Cuando:** toco "Iniciar". **Entonces:** la app pide confirmar ("¿Empezar la orden N° X?") antes de enviar nada; si cancelo, no cambia nada.
2. **Dado:** la confirmación. **Cuando:** confirmo. **Entonces:** la orden pasa a `En curso`, queda un evento con el usuario de la escuadrilla y la fecha, y el detalle y la lista la muestran "En curso" sin el botón.
3. **Dado:** una orden que ya está `En curso` (por ejemplo, un doble toque o un reintento). **Cuando:** se pide iniciarla de nuevo. **Entonces:** responde bien, no cambia nada y no se duplica el evento.
4. **Dado:** una orden de otra escuadrilla, una que no está `Asignada` ni `En curso`, una desasignada o un id inexistente. **Cuando:** intento iniciarla. **Entonces:** recibo 404, sin distinguir el motivo (como en E05-02).
5. **Dado:** una orden prevista para otro día. **Cuando:** la inicio. **Entonces:** se permite: la fecha prevista es orientativa.
6. **Dado:** una escuadrilla con otra orden `En curso`. **Cuando:** inicia una más. **Entonces:** se permite, sin límite.
7. **Dado:** un usuario de administración o dirección. **Cuando:** llama a la API para iniciar. **Entonces:** recibe acceso denegado (403).
8. **Dado:** un error de conexión al iniciar. **Cuando:** falla el envío. **Entonces:** la app lo avisa y la orden sigue `Asignada` en pantalla, para reintentar.

## Decisiones

- **Se mantiene el botón "Iniciar"** (negocio, 2026-10-26), aunque el prototipo del cliente cierra directo sin iniciar: así administración ve qué orden se está trabajando.

Validadas con negocio el 2026-10-26 al refinar:

- **Varias en curso**: una escuadrilla puede tener más de una orden `En curso` a la vez.
- **Cualquier día**: se puede iniciar una orden prevista para otro día.
- **Confirmar antes, sin deshacer**: se pide confirmación dentro de la app (no un diálogo del navegador). No hay vuelta de `En curso` a `Asignada`; si se inició por error, se avisa a la oficina.

## Fuera de alcance

- Registro de hora de llegada y salida: confirmado que NO se registra. El evento de inicio es solo el cambio de estado.
- Deshacer el inicio.
- Que administración vea las órdenes en curso: es del panel (E04-05) y del detalle de administración (E04-06). Esta historia deja el estado y el evento.

## Notas técnicas

- Endpoint `POST /tech/orders/{id}/start` con `require_role(technician)`. Usa el mismo filtro que E05-02 (orden abierta con la asignación vigente de la escuadrilla del usuario); si no cumple, 404 `order_not_found`.
- Si está `Asignada`, aplica la acción `start` de la máquina de estados (`apply_transition`, evento `status_change` con el usuario). Si ya está `En curso`, devuelve la orden sin tocar nada. Si otro la cambió al mismo tiempo, 409 `order_status_conflict`.
- Es idempotente por estado (criterio 3), así que no necesita una clave de idempotencia aparte; la clave queda para el cierre (E05-12).
- Responde el detalle actualizado (`OrderDetailTechnicianOut`). La PWA lo guarda en la caché del detalle e invalida la lista.
