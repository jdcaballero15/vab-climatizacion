---
id: E04-02
title: "Crear una orden de trabajo"
epic: E04
phase: 1
priority: must
status: ready
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E04-01, E03-02, E02-01]
blocked_by: []
assumes: []
---

# E04-02 Crear una orden de trabajo

## Historia

**Como** administración, **quiero** crear una orden de trabajo a partir de un pedido de un cliente (llega por WhatsApp, mail, teléfono o en persona), **para** que el pedido quede registrado y no se pierda.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea una orden con cliente, domicilio, tipo de trabajo, canal y descripción. **Entonces:** queda en estado `Pendiente` con un número correlativo legible.
2. **Dado:** una orden recién creada. **Cuando:** se guarda. **Entonces:** queda un evento de creación con usuario y fecha.
3. **Dado:** el pedido. **Cuando:** creo la orden. **Entonces:** elijo el canal (WhatsApp, mail, teléfono o presencial) y puedo anotar, si quiero, quién pidió (nombre y cargo) y dónde (sector, piso o ala).
4. **Dado:** un cliente con un solo domicilio activo. **Cuando:** lo elijo. **Entonces:** el domicilio se completa solo. Con varios, administración elige uno, sin valor por defecto.
5. **Dado:** un cliente sin domicilio activo. **Cuando:** creo la orden. **Entonces:** puedo agregar el domicilio sin salir de la pantalla.
6. **Dado:** datos obligatorios faltantes. **Cuando:** se intenta guardar. **Entonces:** se indica cuáles faltan (en la pantalla y con 422 en la API).
7. **Dado:** un domicilio de otro cliente o inactivo, o un tipo de trabajo inactivo. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422. Un cliente, domicilio o tipo inexistente da 404.
8. **Dado:** órdenes creadas. **Cuando:** administración abre "Órdenes pendientes". **Entonces:** ve las órdenes `Pendiente` con número, cliente, domicilio, tipo de trabajo y fecha de creación, de la más vieja a la más nueva.
9. **Dado:** un técnico o dirección. **Cuando:** llama a la API de creación. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Asociar un equipo a la orden: E04-12.
- Panel de órdenes por estado con filtros: E04-05. Acá solo el listado de pendientes, que es desde donde se asigna (E04-03).
- Detalle de la orden con línea de tiempo: E04-06. Editar o cancelar la orden: E04-07 y siguientes.
- Órdenes de taller (E06-01) y órdenes generadas por mantenimiento (E07-04).

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Canal obligatorio**: WhatsApp, mail, teléfono o presencial (en la oficina o pedido al técnico en el lugar).
- **Solicitante en dos campos opcionales**: quién pidió (nombre y cargo, texto libre) y dónde (sector, piso o ala). Reemplaza lo que Persat cargaba en solicitante, cargo, sector y piso, muy usado en sanatorios y organismos públicos. El técnico va a ver el sector, no el nombre (E05-02).
- La descripción del pedido es obligatoria.

## Notas técnicas

- Columnas nuevas en `work_order`: `channel` (enum `order_channel`: `whatsapp`, `email`, `phone`, `in_person`), `requester_name` y `requester_area`, opcionales. `source = manual`; las de mantenimiento usan `source = maintenance` (E07-04). Actualizar `data-model.dbml`.
- Creación y evento `created` en la misma transacción, con el servicio de E04-01.
- Endpoints `POST /admin/orders` y `GET /admin/orders?status=pending` (paginado como `/admin/clients`), con `require_role(admin)`. El esquema de entrada rechaza `number` y `status`.
- Web-admin: pantalla "Órdenes" con el listado de pendientes y el formulario de alta. El alta de domicilio en el lugar reutiliza el formulario de E03-02.
- La numeración arranca en 1. Si la importación del historial de Persat (E11-03) necesita conservar sus números, ajusta la secuencia ahí.

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): `POST /admin/orders` y `GET /admin/orders?status=pending` (paginado con `limit` y `offset`), con `require_role(admin)`. `status` es obligatorio y por ahora solo acepta `pending`; el resto de los filtros llega con E04-05. Migración `b4e1c7a20d93`: enum `order_channel` y columnas `channel`, `requester_name` y `requester_area`, nulas en la base (las de mantenimiento no tienen canal) y con el canal obligatorio en la API.
- El alta y el evento `created` (sin estado anterior, con `Pendiente` como estado nuevo, usuario y fecha) van en una transacción. La fecha de creación que devuelven el alta y el listado es la del evento (ADR 0005). El listado ordena por esa fecha y después por número.
- Texto: la descripción es obligatoria; en blanco da 422. Quién y dónde se guardan recortados, y vacíos quedan sin dato.
- Errores: 404 `client_not_found`, `site_not_found`, `work_type_not_found`; 422 `site_of_another_client`, `site_inactive`, `work_type_inactive`. La validación del domicilio pasa de `services/equipment.py` a `clients_service.check_active_site_of_client`, compartida con equipos.
- Para elegir el cliente, el web-admin usa `/admin/clients/similar?name=` (sin mayúsculas ni acentos, contenido en el nombre). Esa búsqueda compara por contención desde 4 letras; buscar por número de cliente queda para E03-06.
