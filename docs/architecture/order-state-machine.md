# Máquina de estados de la orden de trabajo

Los siete estados los pidió el cliente: **Pendiente, Asignada, En curso, Terminada, Facturada, Cobrada, Cancelada**.

> Las transiciones de esta página se validaron con negocio el 2026-10-26 (refinamiento de E04-01). La reasignación se sumó el 2026-10-27 (refinamiento de E04-04). Lo que sigue abierto figura en [decisiones pendientes](../domain/decisiones-pendientes.md).

## Diagrama

```mermaid
stateDiagram-v2
  [*] --> Pendiente: administración crea la orden
  [*] --> Pendiente: mantenimiento generado (requiere aprobación en bloque)

  Pendiente --> Asignada: administración asigna escuadrilla
  Asignada --> Pendiente: administración desasigna
  Asignada --> Asignada: administración reasigna a otra escuadrilla
  EnCurso --> Asignada: administración reasigna (con confirmación)
  Asignada --> EnCurso: escuadrilla inicia
  EnCurso --> Terminada: escuadrilla cierra (resuelta)
  EnCurso --> Pendiente: escuadrilla marca "requiere otra visita" o "no se pudo hacer"
  EnCurso --> EnCurso: "requiere retiro" convierte en orden de taller

  Terminada --> Facturada: administración revisa y registra factura
  Terminada --> Asignada: administración devuelve a la escuadrilla (con motivo)
  Facturada --> Cobrada: administración registra cobro

  Pendiente --> Cancelada: administración cancela (con motivo)
  Asignada --> Cancelada: administración cancela (con motivo)
  EnCurso --> Cancelada: administración cancela (con motivo)

  Cobrada --> [*]
  Cancelada --> [*]
```

`EnCurso` es el estado `En curso`. Mermaid no admite espacios en los identificadores.

## Reglas

| # | Regla |
|---|---|
| R1 | Solo administración crea, asigna, revisa, factura, cobra y cancela. Solo la escuadrilla asignada (su usuario, rol `technician`) inicia y cierra. |
| R2 | Cada cambio de estado inserta un `work_order_event` con actor y fecha. Las fechas de la orden salen de ahí. |
| R3 | Cancelar exige motivo y solo es posible antes de `Terminada`. |
| R4 | `Facturada` exige número de factura. `Cobrada` solo desde `Facturada`. |
| R5 | `Cobrada` y `Cancelada` son finales. Una corrección es una nueva orden o un ajuste con auditoría, no una reapertura. |
| R6 | Una orden con `requires_approval = true` no se puede asignar hasta que administración apruebe el lote. |
| R7 | Cada orden (o etapa, en taller) tiene una sola escuadrilla responsable (D-013). Se asigna con fecha prevista, sin hora. Quiénes fueron se registra al cerrar. |
| R8 | Devolver a la escuadrilla una orden `Terminada` exige motivo y la deja `Asignada` a la misma escuadrilla. |
| R9 | Reasignar cierra la asignación vigente y abre la nueva en una transacción. Una orden `En curso` reasignada queda `Asignada` para la nueva escuadrilla, que la tiene que iniciar. Desasignar solo es posible desde `Asignada` (E04-04). |

## Órdenes de taller (retiro, taller y devolución)

Una orden `workshop` tiene tres etapas **en fila** (decisión del 2026-11-03, nota en el ADR 0007): retiro, galpón y devolución. `work_order.workshop_stage` dice cuál toca. Cada etapa se asigna, se inicia y se cierra como una orden en el lugar:

| Cierre de la etapa | Efecto |
|---|---|
| Retiro hecho | Vuelve a `Pendiente` con la etapa Galpón (acción `complete_stage`), sin escuadrilla |
| Trabajo en el galpón terminado | Vuelve a `Pendiente` con la etapa Devolución |
| Devolución hecha | `Terminada` |
| Requiere otra visita o No se pudo hacer | Vuelve a `Pendiente` en la misma etapa |

Retiro y devolución hechos exigen firma y nombre del cliente (sin DNI); el galpón no se firma. La orden se factura una sola vez, al quedar `Terminada`. "En el galpón" son las de taller con el retiro hecho y la devolución sin hacer.

## Cierre de la escuadrilla y resultados

| Resultado elegido | Efecto |
|---|---|
| Resuelta | La orden pasa a `Terminada` |
| Requiere retiro | La misma orden pasa a `workshop`, se crean las etapas y sigue `En curso` |
| Requiere otra visita | Vuelve a `Pendiente` sin escuadrilla ni fecha, para reprogramarla (se puede asignar a otra), conservando lo registrado |
| No se pudo hacer (con motivo) | Igual que "requiere otra visita": vuelve a `Pendiente` sin escuadrilla ni fecha, con el motivo visible para la oficina. Sin estado "No realizada" (E05-08) |

## Puntos sin resolver

- **Revisión**: la propuesta técnica muestra "Revisión" como paso entre Terminada y Facturada, pero no es uno de los siete estados del cliente. Se modela como una acción de administración sobre `Terminada` (aprobar o devolver), no como estado. Ver `D-005`.
- **Aprobación en bloque** de mantenimiento: se modela con el campo `requires_approval`, no con un estado extra. Ver `D-005`.
