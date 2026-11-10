---
id: E09-01
title: "Generar el comprobante PDF de retiro"
epic: E09
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E06-04, E00-09]
blocked_by: []
assumes: []
---

# E09-01 Generar el comprobante PDF de retiro

## Historia

**Como** administración, **quiero** generar un PDF del retiro de un equipo con la firma del cliente, **para** enviarle al cliente constancia de lo que se llevó.

## Criterios de aceptación

1. **Dado:** una etapa de retiro completada. **Cuando:** administración genera el comprobante. **Entonces:** se crea un PDF con cliente, equipo, fecha, técnico, estado declarado, nombre y DNI de quien firmó y la imagen de la firma.
2. **Dado:** el PDF. **Cuando:** se genera. **Entonces:** no incluye precios.
3. **Dado:** un comprobante generado. **Cuando:** se vuelve a pedir. **Entonces:** se devuelve el mismo archivo almacenado.
4. **Dado:** una etapa de retiro sin completar. **Cuando:** se pide el comprobante. **Entonces:** se rechaza.

## Notas técnicas

- El PDF se guarda en el bucket. El DNI y la firma son datos personales: ver `SECURITY.md`.

## Decisiones (Gonza)

- Sin DNI: el retiro pide firma y nombre (2026-11-03). El criterio 1 queda sin DNI.

## Hecho

- PDF con fpdf2 (Python puro, nueva dependencia del backend). Se arma en el servidor (`app/services/pdf.py`) y se guarda en el bucket bajo `documents/`, con su `stored_file`; `order_document` lo ata a la orden, uno por tipo.
- `POST /admin/orders/{id}/documents/{pickup_receipt|delivery_receipt}` (administración) devuelve una URL firmada; la segunda vez devuelve el mismo archivo. Sin la etapa cerrada como hecha con firma, 409 `stage_not_done`.
- web-admin: "Comprobante de retiro" y "Comprobante de devolución" en el detalle de una orden de taller.
- Lleva cliente, domicilio, equipo, fecha, escuadrilla, técnicos, estado del equipo, nombre de quien firmó y la imagen de la firma.
