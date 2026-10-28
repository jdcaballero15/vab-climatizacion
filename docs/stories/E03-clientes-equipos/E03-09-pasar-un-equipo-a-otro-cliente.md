---
id: E03-09
title: "Pasar un equipo a otro cliente"
epic: E03
phase: 2
priority: should
status: draft
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-03]
blocked_by: []
assumes: [D-002]
---

# E03-09 Pasar un equipo a otro cliente

## Historia

**Como** administración, **quiero** pasar un equipo a otro cliente cuando lo venden o lo trasladan, **para** seguir atendiéndolo sin cargarlo de nuevo.

## Criterios de aceptación

1. **Dado:** un equipo de un cliente. **Cuando:** administración lo pasa a un domicilio activo de otro cliente. **Entonces:** el equipo queda en ese cliente y domicilio con un **código nuevo**, generado con el número del cliente nuevo (mismas reglas que el alta, E03-03).
2. **Dado:** un equipo trasladado. **Cuando:** administración abre su ficha. **Entonces:** ve el traslado registrado: cliente y código anteriores, quién lo hizo y cuándo. Buscando por el código anterior lo encuentra.
3. **Dado:** un equipo con trabajos hechos. **Cuando:** se lo pasa a otro cliente. **Entonces:** las órdenes anteriores siguen siendo del cliente original y no aparecen en los informes del cliente nuevo; en la ficha del equipo, la administración las ve marcadas como anteriores al traslado.
4. **Dado:** un domicilio inactivo o inexistente. **Cuando:** se intenta pasar el equipo ahí. **Entonces:** se rechaza con mensaje claro.

## Notas técnicas

- Respuesta del cliente (2026-10-28): un equipo puede pasar de un cliente a otro (venta o traslado).
- Hoy E03-03 solo permite mudar un equipo entre domicilios del mismo cliente.
- Respondido por Gonza (2026-10-28): código nuevo, pero tiene que quedar registro del anterior. Propuesta: tabla de traslados (`equipment_transfer`: equipo, cliente y código de origen y destino, quién y cuándo), sin borrar nada.

## Preguntas abiertas

- Propuesta a confirmar: el cliente nuevo no ve en sus informes los trabajos anteriores al traslado (eran de otro cliente); la administración sí los ve en la ficha del equipo.

## Fuera de alcance

- Unificar dos clientes: E03-08.
