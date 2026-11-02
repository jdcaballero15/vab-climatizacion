# ADR 0005: Reglas de datos

**Estado:** Aceptado

## Contexto

El cliente necesita historial confiable por cliente y por equipo, estadísticas sobre términos estandarizados, y no perder información en el traspaso entre oficina y campo.

## Decisión

1. **Borrado lógico.** Todas las tablas tienen `deleted_at`. No existe `DELETE` físico en la aplicación. Los repositorios filtran borrados por defecto. Una restauración es un `UPDATE`.
2. **Fechas de negocio y precios en tablas de transacción.** La entidad padre (por ejemplo `work_order`) no guarda "fecha de cierre", "fecha de factura" ni precios. Esos datos viven en `work_order_event`, `invoice_record`, `payment_record`, `part_price`, `part_usage`, `stock_movement` y similares. Los timestamps técnicos (`created_at`, `updated_at`, `deleted_at`) sí van en todas las tablas. *Esta es la interpretación aplicada de la regla del proyecto; validar con negocio.*
3. **Precio estampado al usar.** Cuando un repuesto se usa en una orden, `part_usage.unit_price` guarda el precio vigente en ese momento. Cambiar la lista de precios después no altera órdenes pasadas. *Ajuste del 2026-11-02 (E05-05, acordado con Gonza):* el precio se estampa cuando administración **aprueba** la orden, no cuando la escuadrilla carga el material. Hasta aprobarla, la orden toma el precio vigente. Motivo: los precios arrancan en $0 y se completan después; si se estampara al usar, las primeras órdenes quedarían en $0.
4. **Fotos y firmas fuera de la base.** La base guarda solo la clave del objeto y sus metadatos. Los archivos viven en el bucket y se sirven con URLs firmadas de corta duración.
5. **Stock por movimientos.** El stock actual por ubicación es la suma de `stock_movement`. Nunca se edita un número de stock directamente.
6. **Catálogos estandarizados con "Otro".** Fallas y reparaciones se eligen de una lista. "Otro" exige observación, y administración puede promover un texto repetido a la lista.
7. **Auditoría.** Cambios sobre órdenes, catálogos, precios y stock quedan en `audit_log` con quién, cuándo y qué cambió.
8. **Migraciones.** Alembic, reversibles, revisadas a mano.

## Consecuencias

- Consultas de estado actual requieren el último evento. Se guarda `work_order.status` como columna derivada, mantenida por el servicio dentro de la misma transacción que inserta el evento.
- El historial es completo y se puede reconstruir cualquier fecha.
- Las migraciones de datos de Persat quedan registradas en `legacy_reference` y no ensucian las entidades.
