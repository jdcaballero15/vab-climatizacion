---
id: E03-10
title: "Datos técnicos del equipo: frigorías, gas y alimentación"
epic: E03
phase: 1
priority: should
status: done
roles: [admin, technician]
size: S
areas: [backend, web-admin, pwa-tecnico]
depends_on: [E03-03]
blocked_by: []
assumes: [D-002]
---

# E03-10 Datos técnicos del equipo: frigorías, gas y alimentación

## Historia

**Como** administración, **quiero** guardar en cada equipo su potencia en frigorías, el gas refrigerante y la alimentación eléctrica, **para** saber qué equipo es sin tener que ir a verlo y que la escuadrilla llegue sabiendo con qué se va a encontrar.

## Criterios de aceptación

1. **Dado:** un equipo. **Cuando:** administración lo crea o lo edita. **Entonces:** puede cargar, además de marca y modelo, las frigorías (número entero), el gas (de una lista) y la alimentación (220 V o 380 V). Los tres son opcionales.
2. **Dado:** un gas o una alimentación que no están en la lista, o frigorías en cero, negativas o con decimales. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
3. **Dado:** un equipo con esos datos. **Cuando:** administración abre la lista de equipos del cliente o la ficha del equipo. **Entonces:** los ve.
4. **Dado:** una orden con equipo. **Cuando:** la escuadrilla la abre en el celular. **Entonces:** ve también frigorías, gas y alimentación.
5. **Dado:** un equipo de antes de este cambio (o importado de Persat). **Cuando:** se lo muestra. **Entonces:** esos datos aparecen vacíos y el resto sigue igual.

## Decisiones

- Pedido de Agus (2026-11-24): "agregar una marca, agregarle la potencia, de cuántas frigorías, el tipo de gas y la alimentación, que sería 220 o 380". Gonza lo confirmó el 2026-11-25. Cambia la decisión de E03-03 ("no se guardan potencia ni gas refrigerante como campos propios").
- Gases: R22, R410A, R32, R407C, R404A, R134a, R290 y "Otro" (el detalle va en observaciones). La lista vive en el código (`app/domain/equipment.py`), no en la base: sumar uno no necesita migración.
- Alimentación: `220` (monofásica) o `380` (trifásica).

## Notas técnicas

- Columnas nuevas en `equipment`, nulas: `capacity_frigorias` (entero), `refrigerant` (texto corto) y `power_supply` (texto corto). La validación de la lista la hace el esquema de la API.
- `EquipmentTechnicianOut` suma los tres datos: no son precios, mano de obra ni historial del cliente.

## Hecho

- Migración `a7d3e9f1b520`: `capacity_frigorias`, `refrigerant` y `power_supply` en `equipment`, nulas. Las listas en `app/domain/equipment.py` (`Refrigerant`, `PowerSupply`); frigorías enteras mayores a cero (`strict`: ni texto ni decimales).
- API de equipos de administración y `EquipmentTechnicianOut` con los tres datos.
- web-admin: campos Frigorías, Gas y Alimentación en el alta y la edición; en la lista, "4.500 frigorías · Gas R32 · 380 V"; en la ficha, cada dato por separado.
- pwa-tecnico: fila "Datos del equipo" en el detalle de la orden, solo si hay algo cargado.

## Fuera de alcance

- Que el técnico dé de alta el equipo desde el celular: E05-15.
- Convertir frigorías a otras unidades (BTU, kW, toneladas).
