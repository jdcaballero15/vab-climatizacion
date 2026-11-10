---
id: E09-02
title: "Generar el comprobante PDF de devolución"
epic: E09
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E06-06, E09-01]
blocked_by: []
assumes: []
---

# E09-02 Generar el comprobante PDF de devolución

## Historia

**Como** administración, **quiero** generar un PDF de la devolución de un equipo con la firma del cliente, **para** enviarle al cliente constancia de lo recibido.

## Criterios de aceptación

1. **Dado:** una etapa de devolución completada. **Cuando:** administración genera el comprobante. **Entonces:** se crea un PDF con cliente, equipo, fecha, trabajo realizado, nombre y DNI de quien firmó y la firma.
2. **Dado:** el PDF. **Cuando:** se genera. **Entonces:** no incluye precios salvo que negocio indique lo contrario.
3. **Dado:** una etapa sin completar. **Cuando:** se pide el comprobante. **Entonces:** se rechaza.

## Decisiones (Gonza)

- La devolución incluye el resumen del trabajo (falla, reparación y observación del galpón) y los materiales usados, sin precios (2026-11-10). Sin DNI.

## Hecho

- PDF con fpdf2 (Python puro, nueva dependencia del backend). Se arma en el servidor (`app/services/pdf.py`) y se guarda en el bucket bajo `documents/`, con su `stored_file`; `order_document` lo ata a la orden, uno por tipo.
- `POST /admin/orders/{id}/documents/{pickup_receipt|delivery_receipt}` (administración) devuelve una URL firmada; la segunda vez devuelve el mismo archivo. Sin la etapa cerrada como hecha con firma, 409 `stage_not_done`.
- web-admin: "Comprobante de retiro" y "Comprobante de devolución" en el detalle de una orden de taller.
