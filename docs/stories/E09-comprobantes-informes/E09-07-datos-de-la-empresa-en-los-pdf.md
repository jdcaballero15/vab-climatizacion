---
id: E09-07
title: "Logo y datos de la empresa en el encabezado de los PDF"
epic: E09
phase: 1
priority: should
status: done
roles: [admin]
size: S
areas: [backend]
depends_on: [E09-01, E09-02, E09-04, E04-09]
blocked_by: []
assumes: []
---

# E09-07 Logo y datos de la empresa en el encabezado de los PDF

## Historia

**Como** administración, **quiero** que los PDF que se le dan al cliente lleven el logo, el CUIT y el domicilio de la empresa, **para** que el comprobante se vea formal y el cliente sepa quién lo emite.

## Criterios de aceptación

1. **Dado:** el CUIT y el domicilio cargados en la configuración. **Cuando:** se genera un comprobante de retiro o devolución, un informe mensual o un detalle de factura. **Entonces:** debajo del nombre de la empresa sale "CUIT ... · domicilio".
2. **Dado:** uno solo de los dos datos. **Cuando:** se genera el PDF. **Entonces:** sale solo ese.
3. **Dado:** ninguno de los dos. **Cuando:** se genera el PDF. **Entonces:** sale con el logo y el nombre, sin la línea de datos.
4. **Dado:** cualquier PDF. **Cuando:** se genera. **Entonces:** lleva el ícono del logo de VAB a la izquierda del nombre.

## Decisiones

- Pedido de Agus (2026-11-24): "agregar datos fiscales, domicilio, el CUIT, ver el logo". Gonza pasó el CUIT, el domicilio y el logo el 2026-11-25.
- El logo es material público de la marca: va en el repositorio (`backend/app/assets/logo.png`), solo el ícono, azul sobre transparente, sacado de la imagen original (azul sobre negro).
- **El CUIT y el domicilio no van en el código:** el repositorio es público y el CUIT es de una persona. Se cargan en el hosting con `COMPANY_TAX_ID` y `COMPANY_ADDRESS` (y el nombre, si hace falta, con `COMPANY_NAME`).

## Notas técnicas

- `pdf.CompanyHeader` y `pdf.company_header(settings)`; los tres armadores de PDF reciben el encabezado. El logo, `pdf.LOGO`, mide 16 mm de alto.
- Los comprobantes de retiro y devolución se guardan la primera vez que se piden: los que ya existían no cambian.

## Preguntas abiertas

- Razón social y condición frente al IVA: ¿van? Con un CUIT de persona, la razón social puede no ser "VAB Climatización".
- ¿Agus se refería al comprobante de taller (el único PDF que sale al cerrar) o quiere un PDF al cerrar cualquier orden? Lo segundo sería otra historia.

## Fuera de alcance

- Un PDF al cerrar las órdenes en el lugar.
