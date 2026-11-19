---
id: E00-06
title: "Despliegue a producción por tag con aprobación"
epic: E00
phase: 1
priority: must
status: draft
roles: [dev]
size: S
areas: [infra]
depends_on: [E00-05]
blocked_by: []
assumes: []
---

# E00-06 Despliegue a producción por tag con aprobación

## Historia

**Como** equipo de desarrollo, **quiero** publicar en producción al crear un tag de versión, con aprobación manual, **para** controlar qué llega a producción y poder volver atrás.

## Criterios de aceptación

1. **Dado:** un tag `vMAJOR.MINOR.PATCH`. **Cuando:** se crea. **Entonces:** el workflow espera una aprobación manual antes de desplegar.
2. **Dado:** un despliegue fallido. **Cuando:** falla el chequeo de salud. **Entonces:** se revierte a la versión anterior.
3. **Dado:** una versión desplegada. **Cuando:** se consulta el endpoint de versión. **Entonces:** devuelve el tag y el commit.

## Notas técnicas

- Desde el 2026-11-19 hay un ambiente develop (ADR 0011): la rama `develop` se despliega sola en un ambiente gratis con datos ficticios, y se publica en producción con un PR de `develop` a `main`. Esta historia, si se retoma, cambiaría ese último paso (el merge a `main`) por un tag con aprobación.
