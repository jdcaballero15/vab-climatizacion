# Alcance vigente de la Fase 1

Versión para el repositorio. No incluye precios, horas ni acuerdos comerciales, que se gestionan fuera de este repo.

## Qué incluye

- Circuito completo, del pedido al cobro.
- App de administración (PC o tablet) y app del técnico (celular Android de la empresa).
- Catálogos editables por administración.
- Mantenimiento preventivo automático con checklist por frecuencia y tipo de equipo.
- Órdenes de taller unificadas (retiro, taller y devolución como etapas de una sola orden).
- Comprobantes PDF de retiro y devolución, e informe mensual por mail a cada cliente.
- Tablero de seguimiento.
- Stock de repuestos por depósito y por camioneta (se movió desde la Fase 2).
- Migración de clientes y equipos, y del historial de trabajos de Persat (se sumó).
- Capacitación y convivencia con Persat.

## Qué no incluye

| Tema | Estado |
|---|---|
| Código QR por equipo | Fuera por ahora. El cliente dijo "lo evaluaría". Ver `E99-01` |
| Registro de hora de llegada y salida del técnico | **Confirmado que NO**. Fuera de alcance |
| Facturación electrónica | Fuera. El sistema registra número de factura y cobro, pero la factura se emite en el sistema de facturación del cliente |
| Portal de clientes | Fuera. El historial llega en el informe mensual por mail |
| Envío de informes por WhatsApp | Fuera por ahora. Ver `E99-02` |
| Agentes de IA dentro del producto | Fuera por ahora. Ver `E99-03` |

## Datos de dimensionamiento

- 50 a 200 clientes, 200 a 1.000 equipos.
- 4 a 6 técnicos y 2 personas de administración.
- 150 a 300 órdenes por mes en temporada alta, 50 a 150 en baja.
- 50 a 200 repuestos distintos, hoy sin código.

## Estados de la orden

Pendiente, Asignada, En curso, Terminada, Facturada, Cobrada, Cancelada.

## Requisitos transversales

- El técnico trabaja con opciones predefinidas, casi sin escritura libre.
- El técnico nunca ve precios, mano de obra ni historial de clientes.
- Cierre con opciones predefinidas, observación, foto y firma del cliente (con nombre y DNI).
- Todo queda asociado al cliente y a cada equipo.
- Se puede seguir el avance a distancia desde el celular.
- Estandarizar términos para poder medir estadísticas.
- Costos de operación lo más bajos posible.

## Cambio de paradigma

La propuesta original usaba Power Apps, Power Automate y listas de SharePoint sobre Microsoft 365. El proyecto pasa a un **sistema a medida**. Efecto sobre el alcance:

| Antes | Ahora |
|---|---|
| Licencias M365 para técnicos (4 a 6) | No hacen falta |
| Power BI Pro para el dueño | No hace falta, el tablero es parte del sistema |
| Sin costo de hosting | Hay costo recurrente de hosting (ver `D-006`) |
| Límites de delegación y umbral de vista de listas | Ya no aplican |
| Edición de listas SharePoint "de las dos formas" | Reemplazada por catálogos en la app (ver `D-003`) |
| Offline no resuelto | Resuelto en `D-001`: la app funciona con conexión y guarda el borrador del cierre (ADR 0009) |
