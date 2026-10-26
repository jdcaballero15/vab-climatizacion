---
id: E05-14
title: "Ver las órdenes hechas esta semana"
epic: E05
phase: 1
priority: should
status: draft
roles: [technician]
size: S
areas: [backend, pwa]
depends_on: [E05-01, E05-04]
blocked_by: []
assumes: []
---

# E05-14 Ver las órdenes hechas esta semana

## Historia

**Como** escuadrilla, **quiero** ver en el celular las órdenes que cerramos en los últimos días, **para** confirmar que el cierre llegó a la oficina sin tener que llamar.

## Criterios de aceptación

1. **Dado:** el usuario de una escuadrilla. **Cuando:** abre la pestaña "Hechas esta semana". **Entonces:** ve las órdenes que su escuadrilla cerró en los últimos 7 días, de la más reciente a la más vieja, con un contador en la pestaña.
2. **Dado:** una orden de la lista. **Cuando:** se muestra. **Entonces:** figura como cerrada y no se puede volver a abrir el cierre desde el celular.
3. **Dado:** la respuesta de la API. **Cuando:** se la inspecciona. **Entonces:** no contiene precios, mano de obra ni historial de clientes.
4. **Dado:** una escuadrilla sin cierres en la semana. **Cuando:** abre la pestaña. **Entonces:** ve un mensaje claro.

## Notas técnicas

- Sale del prototipo del cliente (pestañas "Para hacer" y "Hechas esta semana"). Se separó de E05-01 porque depende del cierre (E05-04).
- "Cerró" se toma del evento de cierre de la escuadrilla, no del estado actual: una orden ya facturada también cuenta.

## Preguntas abiertas

- ¿Cuentan los cierres con "requiere otra visita" (la orden vuelve a Pendiente) y los retiros a taller? En el prototipo cuentan.
- ¿"Esta semana" son los últimos 7 días (como el prototipo) o desde el lunes?
