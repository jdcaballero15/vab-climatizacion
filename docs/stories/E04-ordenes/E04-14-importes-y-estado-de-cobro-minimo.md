---
id: E04-14
title: "Importes y estado de cobro de una orden terminada (versión mínima)"
epic: E04
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-08, E00-04]
blocked_by: []
assumes: [D-004]
---

# E04-14 Importes y estado de cobro de una orden terminada (versión mínima)

## Historia

**Como** administración, **quiero** anotar en cada orden terminada cuánto es de repuestos y cuánto de mano de obra, y si ya está facturada, **para** saber qué falta mandar a cobrar.

Versión mínima pedida por Gonza el 2026-10-30 para mostrarle el circuito a Agustín. Es provisoria: la semana siguiente se define bien con la oficina y se reemplaza o se completa con E04-09 (factura), E04-10 (cobro), E04-11 (mano de obra y otros cargos) y E05-05 (repuestos usados).

## Criterios de aceptación

1. **Dado:** una orden `Terminada`. **Cuando:** administración carga el importe de repuestos y el de mano de obra (en pesos, con centavos, desde 0). **Entonces:** se guardan con quién y cuándo, y se ve el total.
2. **Dado:** una orden `Terminada`. **Cuando:** administración la marca `Facturada` (con número de factura opcional) o la vuelve a `Pendiente de enviar a cobrar`. **Entonces:** se guarda. Sin nada cargado, la orden está `Pendiente de enviar a cobrar`.
3. **Dado:** el listado de terminadas. **Cuando:** administración lo mira. **Entonces:** cada orden muestra el estado de cobro y el total, y se puede filtrar por `Pendiente de enviar a cobrar` o `Facturada`.
4. **Dado:** una orden que no está `Terminada`. **Cuando:** se intenta cargar importes. **Entonces:** se rechaza (409).
5. **Dado:** un importe negativo o con más de dos decimales. **Cuando:** se intenta guardar. **Entonces:** se rechaza (422, con el campo).
6. **Dado:** un técnico o dirección. **Cuando:** intenta cargar importes. **Entonces:** recibe 403. El técnico no ve importes en ninguna respuesta (test de contrato).

## Fuera de alcance

- Catálogo y lista de precios de repuestos, repuestos por ítem y stock (E02-05, E02-06, E05-05, E08).
- Cálculo de la mano de obra por lista, abono o presupuesto (E04-11).
- Estados `Facturada` y `Cobrada` de la orden (E04-09, E04-10): acá el estado de cobro es un dato aparte y la orden sigue `Terminada`.
- Auditoría de cambios de importes: queda solo el último, con quién y cuándo.

## Preguntas abiertas

- Todo lo de `D-004` y las preguntas de E04-09, E04-10 y E04-11: qué datos necesita administración para facturar, si una factura cubre varias órdenes, cómo se calcula la mano de obra y si hace falta registrar el cobro.

## Notas técnicas

- Tabla `work_order_billing`, una por orden (índice único parcial): `parts_amount` y `labor_amount` `NUMERIC(12,2)` con CHECK `>= 0`, `status` (enum `billing_status`: `pending`, `invoiced`), `invoice_number` opcional, `updated_by`. Migración reversible.
- `PUT /admin/orders/{id}/billing` (solo administración) guarda o reemplaza; 404 si la orden no existe, 409 `order_not_done` si no está `Terminada`. `GET /admin/orders?status=done&billing=pending|invoiced` filtra; `OrderListItemOut.billing` trae importes, total, estado, número de factura, quién y cuándo (nulo sin datos cargados).
- `parts_amount`, `labor_amount`, `invoice_number` y `billing` suman a `FORBIDDEN_TECHNICIAN_FIELDS`.
- web-admin: en Terminadas, la tarjeta muestra el estado de cobro y el total; filtro por estado de cobro; en el detalle del cierre, el formulario "Importes y cobro".
- Hecho (un solo PR): `BillingUpdate` y `BillingAdminOut`, servicio `app/services/billing.py`, filtro `billing` en el listado (sin fila de cobro cuenta como pendiente), migración `a8c2e4f6b013`. En web-admin, "Ver cierre y cobro" en las terminadas abre el cierre y el formulario `BillingForm` (acepta coma o punto para los centavos y muestra el total al escribir); la tarjeta muestra el estado de cobro y el total; filtro "Cobro" sobre el listado de terminadas.
