---
id: E05-02
title: "Ver el detalle de una orden asignada"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: S
areas: [backend, pwa]
depends_on: [E05-01]
blocked_by: []
assumes: []
---

# E05-02 Ver el detalle de una orden asignada

## Historia

**Como** técnico, **quiero** abrir una orden y ver lo necesario para hacer el trabajo, **para** llegar y trabajar sin llamar a la oficina.

## Criterios de aceptación

1. **Dado:** una orden asignada a mí. **Cuando:** la abro. **Entonces:** veo cliente, dirección, equipo, tarea e instrucciones de la oficina.
2. **Dado:** el detalle. **Cuando:** lo consulto. **Entonces:** no incluye historial del cliente ni del equipo, ni precios, ni mano de obra.
3. **Dado:** una orden que no está asignada a mi escuadrilla. **Cuando:** intento abrirla por su ID. **Entonces:** recibe 404.
4. **Dado:** una dirección. **Cuando:** la toco. **Entonces:** se abre en la app de mapas del celular.

## Preguntas abiertas

- ¿El técnico puede ver los trabajos anteriores del mismo equipo? Hoy el requisito dice que nunca ve historial de clientes.
