---
id: E12-04
title: "Protección de datos personales"
epic: E12
phase: 1
priority: must
status: draft
roles: [owner]
size: M
areas: [backend, infra]
depends_on: [E00-09]
blocked_by: [D-008]
assumes: []
---

# E12-04 Protección de datos personales

## Historia

**Como** dirección, **quiero** que el DNI y las firmas estén protegidos y con una política de retención definida, **para** cumplir con la ley de protección de datos personales y cuidar a los clientes.

## Criterios de aceptación

1. **Dado:** el DNI de quien firma. **Cuando:** se guarda. **Entonces:** se cifra en reposo.
2. **Dado:** las firmas y fotos. **Cuando:** se piden. **Entonces:** solo se entregan con URLs firmadas de corta duración a usuarios con permiso.
3. **Dado:** la política de retención definida en `D-008`. **Cuando:** se implementa. **Entonces:** hay un procedimiento para anonimizar o eliminar datos vencidos.
4. **Dado:** los comprobantes e informes. **Cuando:** se generan. **Entonces:** incluyen el aviso legal definido en `D-008`.
5. **Dado:** los logs y la auditoría. **Cuando:** se revisan. **Entonces:** no contienen DNI ni firmas.

## Hecho

- Lo que no depende de D-008 ya se cumple: el DNI no se pide (retiro y devolución sin DNI, 2026-11-03), firmas y fotos solo con URLs firmadas de 5 minutos (E00-09), y los logs y la auditoría no guardan DNI ni firmas (E12-01, E12-03). Falta la política de retención y el aviso legal: esperan D-008.
