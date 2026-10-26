# ADR 0009: App del técnico con conexión y borrador local del cierre

- **Estado:** Propuesto
- **Fecha:** 2026-10-26
- **Decide:** Negocio (Gonza, con el relevamiento del cliente)
- **Áreas afectadas:** pwa-tecnico, backend, docs

Reemplaza al [ADR 0003](0003-pwa-offline-first-provisional.md).

---

## Contexto

El ADR 0003 diseñó la app del técnico offline-first mientras no se supiera si en campo hay señal (`D-001`). Los formularios del cliente se contradecían. En el relevamiento, el cliente dijo que las cuadrillas siempre tienen señal, y por eso el diseño original ya había descartado el modo offline.

El offline completo es lo más caro de la app (guardar órdenes en el celular, cola de sincronización, conflictos con la oficina). Si no hace falta, conviene no construirlo. Sigue existiendo un riesgo chico: que la conexión se corte justo mientras el técnico carga un cierre, y que se pierda lo cargado.

## Decisión

> La app del técnico funciona solo con conexión, y guarda en el celular el borrador del cierre que se está cargando para no perderlo si se corta la señal.

- Las órdenes, el detalle y los catálogos se piden al servidor. Sin conexión, la app avisa que no hay señal; no muestra órdenes guardadas.
- Mientras el técnico carga un cierre (falla, reparación, repuestos, observación, fotos, firma), lo cargado se guarda en el celular como borrador.
- Si al enviar no hay conexión, o se corta a mitad, el borrador queda guardado y se envía solo al volver la señal. Si el técnico cierra la app, al abrirla sigue ahí.
- El envío usa la clave de idempotencia del cierre (E05-12), así que reintentar no duplica nada.
- El borrador nunca contiene precios, mano de obra ni historial del cliente (son datos que el técnico ya no recibe).
- La carcasa de la app sigue en el service worker (E00-03): abre sin conexión, pero solo para mostrar el aviso y los borradores pendientes.

## Alternativas consideradas

| Alternativa | Ventajas | Por qué se descartó |
|---|---|---|
| Offline-first completo (ADR 0003) | Trabajar en cámaras, sótanos o zonas rurales sin señal | El cliente dijo que siempre hay señal. Suma tres historias grandes (E99-06 a E99-08) y la resolución de conflictos con la oficina |
| Solo con conexión, sin borrador | Lo más simple | Un corte a mitad de un cierre hace perder la firma y las fotos, y el técnico tendría que volver a pedírselas al cliente |

## Consecuencias

**Positivas**
- Las tres historias de offline de la épica E05 pasan al icebox (E99-06, E99-07 y E99-08). No hay cola de sincronización ni conflictos con la oficina.
- El backend no cambia: la idempotencia del cierre (E05-12) ya cubre los reintentos.

**Negativas o costo que aceptamos**
- Sin señal, el técnico no puede ver sus órdenes. Si en la práctica aparecen lugares sin señal, hay que retomar las historias del icebox.

**Qué se vuelve más difícil de ahora en adelante**
- Pasar a offline completo más adelante: el borrador local es una base, pero faltaría guardar las órdenes y resolver conflictos.

## Impacto en las reglas del repositorio

- [x] [`CLAUDE.md`](../../../CLAUDE.md): descripción de `pwa-tecnico/`
- [x] Historias afectadas en `docs/stories/`: las historias de offline pasan al icebox (E99-06 a E99-08); nueva E05-13

## Referencias

- `D-001` en [decisiones pendientes](../../domain/decisiones-pendientes.md).
- ADR 0003 (reemplazado). Historias E05-12, E05-13, E00-03, E01-02.
