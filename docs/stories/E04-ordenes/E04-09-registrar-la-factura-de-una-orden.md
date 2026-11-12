---
id: E04-09
title: "Registrar la factura de una orden"
epic: E04
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E04-08]
blocked_by: []
assumes: [D-004]
---

# E04-09 Registrar la factura de una orden

## Historia

**Como** administración, **quiero** registrar el número de factura de una orden revisada, **para** llevar el control de lo facturado sin duplicar la carga en otro lado.

## Criterios de aceptación

1. **Dado:** una orden `Terminada` y revisada. **Cuando:** administración registra un número de factura. **Entonces:** pasa a `Facturada` y queda un registro de factura con usuario y fecha.
2. **Dado:** una orden sin revisar. **Cuando:** se intenta registrar la factura. **Entonces:** se rechaza.
3. **Dado:** un número de factura vacío. **Cuando:** se intenta guardar. **Entonces:** se rechaza.
4. **Dado:** una orden `Facturada`. **Cuando:** administración corrige el número de factura. **Entonces:** queda auditado el valor anterior y el nuevo.

## Fuera de alcance

- Emisión de la factura electrónica: se sigue haciendo en el sistema de facturación del cliente.

## Decisiones (Gonza, 2026-11-10)

- Una misma factura puede cubrir varias órdenes (por ejemplo, las de un abonado): se eligen en Terminadas y se factura en bloque. Si alguna no se puede (sin aprobar o no terminada), no se factura ninguna y el mensaje dice cuáles.
- Se guardan número y fecha de la factura (D-004 queda resuelta así).
- "Revisada" es "aprobada" (E04-08): sin aprobar no se factura.

## Hecho

- Tablas `invoice` y `work_order_invoice` (una factura vigente por orden). `POST /admin/invoices` pasa las órdenes a Facturada con un evento "Factura N del dd/mm/aaaa"; `PUT /admin/invoices/{id}` corrige número o fecha y deja `invoice_corrected` en la línea de tiempo de cada orden.
- La migración `b3f1d7a9c524` pasa las marcadas "Facturada" en el cobro mínimo de E04-14 a una factura propia y al estado Facturada (sin número, "S/N"). El estado de cobro aparte (`billing_status`) desaparece.
- Facturada, la mano de obra y los cargos ya no se editan.
