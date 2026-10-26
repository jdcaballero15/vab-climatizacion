# ADR 0003: App del técnico como PWA con modo offline

**Estado:** Reemplazado por [ADR 0009](0009-pwa-con-conexion-y-borrador-local.md). Dependía de la decisión `D-001` (conectividad en campo), ya resuelta.

## Contexto

Los formularios del cliente se contradicen: uno dice que siempre hay señal y otro que a veces no (cámaras frigoríficas, sótanos, zonas rurales). Los técnicos usan celulares Android de la empresa.

## Decisión

PWA en React instalable en el celular, sin tiendas de aplicaciones. Se diseña **offline-first** como supuesto de trabajo hasta que el cliente confirme:

- Las órdenes asignadas se guardan en IndexedDB al abrir la app con señal.
- Cerrar una orden, firmar y adjuntar fotos escribe primero en una **cola local** y se sincroniza cuando vuelve la conexión.
- Cada operación de la cola lleva una **clave de idempotencia** (UUID generado en el celular) y el backend la acepta una sola vez.
- Las fotos se suben directo al bucket con URL firmada, con reintento.
- Regla de conflictos: el cierre del técnico se agrega (no pisa). Lo que administra la oficina (asignación, estado) gana el servidor. Si una orden fue reasignada o cancelada mientras el técnico estaba sin señal, el cierre queda en estado "en revisión" para que administración decida.

## Si el cliente responde que siempre hay señal

Se mantiene la PWA pero se retiran las historias marcadas con `blocked_by: D-001` (cola local, sincronización, resolución de conflictos). La API ya es idempotente, así que no hay rehacer nada del backend.

## Consecuencias

- El offline suma trabajo en el cliente (cola, estados "pendiente de sincronizar", pruebas sin red). Por eso conviene resolver `D-001` cuanto antes.
- La firma, foto y el cierre funcionan igual en ambos casos.
- No se necesita publicar en Play Store. Las actualizaciones llegan solas.
