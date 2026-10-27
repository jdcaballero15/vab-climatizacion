---
id: E05-07
title: "Firma del cliente en pantalla con nombre y DNI"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E05-04, E00-09]
blocked_by: []
assumes: [D-011]
---

# E05-07 Firma del cliente en pantalla con nombre y DNI

## Historia

**Como** técnico, **quiero** que el cliente firme en la pantalla e ingrese su nombre y DNI, **para** tener constancia de que el trabajo fue recibido.

## Criterios de aceptación

1. **Dado:** un cierre listo para firmar. **Cuando:** el cliente firma con el dedo y se cargan nombre y DNI. **Entonces:** se guarda la imagen de la firma en el bucket y los datos en el registro de firma.
2. **Dado:** una firma sin nombre o sin DNI. **Cuando:** se intenta enviar el cierre. **Entonces:** se rechaza.
3. **Dado:** el DNI. **Cuando:** se guarda. **Entonces:** se almacena cifrado y no aparece en logs.
4. **Dado:** la firma. **Cuando:** se rota el celular o se vuelve atrás. **Entonces:** no se pierde lo ya trazado.
5. **Dado:** un DNI con formato inválido. **Cuando:** se ingresa. **Entonces:** se avisa (7 u 8 dígitos).

## Preguntas abiertas

- Los formularios del cliente dicen que la firma es obligatoria al cerrar. La propuesta técnica dice "firma del cliente, si corresponde". Ver `D-011`.
- ¿Qué pasa si el cliente no está presente? No se inventa una excepción hasta que negocio la defina.
- ¿Se pide el DNI de quien firma? Depende de `D-008` (retención y texto legal). Si no se pide, se sacan los criterios 3 y 5.

## Notas técnicas

- La imagen de la firma se guarda con el servicio de archivos de E00-09 (PNG, bucket R2) igual que las fotos de E05-06, y viaja en el borrador del celular hasta enviarse (E05-13).
