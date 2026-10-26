---
id: E02-10
title: "Marcar qué tipos de trabajo piden falla y reparación"
epic: E02
phase: 1
priority: must
status: done
roles: [admin]
size: S
areas: [backend, web-admin]
depends_on: [E02-01]
blocked_by: []
assumes: []
---

# E02-10 Marcar qué tipos de trabajo piden falla y reparación

## Historia

**Como** administración, **quiero** indicar en cada tipo de trabajo si al cerrar se pide falla y reparación, **para** que la escuadrilla no tenga que elegirlas en trabajos donde no tienen sentido (instalación, relevamiento).

## Criterios de aceptación

1. **Dado:** un tipo de trabajo. **Cuando:** administración marca o desmarca "Pide falla y reparación". **Entonces:** queda guardado y se ve en la lista de tipos de trabajo.
2. **Dado:** un tipo de trabajo nuevo. **Cuando:** se crea sin indicarlo. **Entonces:** no pide falla y reparación.
3. **Dado:** los tipos de trabajo cargados al aplicar esta historia. **Cuando:** se migra la base. **Entonces:** "Reparación" y "Service" quedan marcados y el resto no (se puede cambiar desde la pantalla).
4. **Dado:** un técnico o dirección. **Cuando:** intenta cambiar la marca. **Entonces:** recibe acceso denegado (403).

## Notas técnicas

- Columna `work_type.requires_failure_repair` (boolean, `false` por defecto), en una migración reversible que marca los existentes por nombre.
- Se edita con el `PATCH` de tipos de trabajo de E02-01. El cierre (E05-04) la lee para exigir falla y reparación.

## Fuera de alcance

- Otras reglas de cierre por tipo de trabajo (por ejemplo, firma obligatoria según el tipo).

## Notas de implementación

- Migración `a1f3c5e7b902`: agrega `requires_failure_repair` con `false` por defecto y marca por nombre (sin distinguir mayúsculas) "Reparación" y "Service". Si alguno fue renombrado, queda sin marcar. El downgrade quita la columna.
- `WorkTypeUpdate` y `WorkTypeAdminOut` suman el campo; cambiar otro campo no toca la marca.
- Web-admin: casilla "Pide falla y reparación al cerrar" en cada tipo de trabajo de la pantalla de catálogos; se guarda al tocarla.
