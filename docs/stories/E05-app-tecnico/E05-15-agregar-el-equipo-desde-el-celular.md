---
id: E05-15
title: "Agregar el equipo desde el celular"
epic: E05
phase: 1
priority: should
status: done
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E03-10, E04-12, E05-02]
blocked_by: []
assumes: [D-002, D-013]
---

# E05-15 Agregar el equipo desde el celular

## Historia

**Como** escuadrilla, **quiero** cargar el equipo en el que estoy trabajando cuando la orden no tiene uno, **para** no trabajar a ciegas y que el equipo quede en el cliente para la próxima vez.

## Criterios de aceptación

1. **Dado:** una orden Asignada o En curso de mi escuadrilla, sin equipo. **Cuando:** cargo el tipo, la ubicación ("Living", "Cocina") y, si los tengo, marca, modelo, frigorías, gas y alimentación. **Entonces:** el equipo se crea en el domicilio de la orden, con el código que genera el sistema, queda asociado a la orden y lo veo en el detalle.
2. **Dado:** el equipo cargado por la escuadrilla. **Cuando:** la oficina abre el cliente o la orden. **Entonces:** lo ve como cualquier otro equipo, y en la línea de tiempo de la orden figura que lo agregó la escuadrilla.
3. **Dado:** una orden que ya tiene equipo. **Cuando:** la escuadrilla intenta agregar otro. **Entonces:** se rechaza (409) y en el celular no se ofrece.
4. **Dado:** una orden de otra escuadrilla, cerrada o inexistente. **Cuando:** se intenta agregar el equipo. **Entonces:** se rechaza como si no existiera (404).
5. **Dado:** falta el tipo o la ubicación, o un dato técnico fuera de la lista, o un tipo de equipo inactivo. **Cuando:** se manda. **Entonces:** se rechaza (422) con el campo y un mensaje claro.
6. **Dado:** administración o dirección. **Cuando:** llaman a la ruta del técnico. **Entonces:** reciben 403.
7. **Dado:** el técnico. **Cuando:** carga el equipo. **Entonces:** solo ve los tipos de equipo activos y el domicilio de su orden; nunca otros equipos, precios ni el historial del cliente.

## Decisiones

- Pedido de Agus (2026-11-24): "estaría bueno que me puedan agregar qué aire es, cosa que ya queda agregado en el cliente". Gonza lo confirmó el 2026-11-25. Cambia lo decidido en octubre (E03-03 y D-002: "el técnico no da de alta equipos").
- Solo se agrega cuando la orden no tiene equipo. Cambiar un equipo mal elegido sigue siendo de la oficina (E04-12); si está mal, la escuadrilla lo anota en la observación del cierre.
- Necesita conexión: si no hay señal, el celular avisa y no se pierde lo escrito mientras la pantalla siga abierta. No entra en el borrador del cierre.

## Notas técnicas

- `GET /tech/equipment-types`: tipos activos, solo id y nombre.
- `POST /tech/orders/{id}/equipment`: crea el equipo con `equipment.create_equipment` en el domicilio de la orden y lo asocia solo si la orden sigue Asignada o En curso y sin equipo (`update_equipment_if` con `only_if_empty`). Evento `equipment_changed` con la nota "Equipo: sin equipo -> <código> (cargado por la escuadrilla)". Devuelve el detalle de la orden del técnico.

## Hecho

- `GET /tech/equipment-types` (activos, id y nombre) y `POST /tech/orders/{id}/equipment` (201 con el detalle de la orden). Errores: 404 `order_not_found`; 409 `order_has_equipment` y `equipment_code_unavailable`; 422 `equipment_type_not_found` y `equipment_type_inactive` (campo `equipment_type_id`), `site_inactive`, y los de validación (ubicación vacía, dato técnico fuera de lista, campos de más como el domicilio).
- `work_orders.add_equipment_for_crew_user`: crea el equipo con `equipment.create_equipment` y lo asocia con `update_equipment_if(only_if_empty=True)`, así no pisa uno que la oficina haya puesto mientras tanto.
- pwa-tecnico: botón "Agregar equipo" en el detalle de una orden sin equipo, con tipo, ubicación, marca, modelo, frigorías, gas y alimentación. Si falla, muestra el mensaje y conserva lo escrito.

## Fuera de alcance

- Cambiar o sacar el equipo desde el celular.
- Fotos del equipo o de la chapa.
- Cargarlo sin conexión.
