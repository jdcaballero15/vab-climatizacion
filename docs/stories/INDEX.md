# Índice de historias

> Generado por `python3 scripts/validate_stories.py --write-index`. No editar a mano.

**Total: 115 historias.** done: 11, draft: 99, icebox: 5

Leyenda: **Bloq.** = decisión abierta que impide implementarla. **Supone** = decisión con propuesta vigente en la que se apoya.

## E00 Fundaciones de plataforma

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E00-01](E00-fundaciones/E00-01-base-del-backend-con-postgresql-y-migraciones.md) | Base del backend con PostgreSQL y migraciones | Debe | S | done | dev | - | - | - |
| [E00-02](E00-fundaciones/E00-02-base-de-la-app-de-administracion.md) | Base de la app de administración | Debe | S | done | dev | - | - | - |
| [E00-03](E00-fundaciones/E00-03-base-de-la-app-del-tecnico-como-pwa-instalable.md) | Base de la app del técnico como PWA instalable | Debe | M | done | dev | - | - | - |
| [E00-04](E00-fundaciones/E00-04-test-de-contrato-el-tecnico-no-ve-precios.md) | Test de contrato: el técnico no ve precios | Debe | S | done | dev | - | - | E00-01 |
| [E00-05](E00-fundaciones/E00-05-elegir-proveedor-de-hosting-y-desplegar-staging.md) | Elegir proveedor de hosting y desplegar staging | Debe | M | draft | dev | D-006 | - | E00-01 |
| [E00-06](E00-fundaciones/E00-06-despliegue-a-produccion-por-tag-con-aprobacion.md) | Despliegue a producción por tag con aprobación | Debe | S | draft | dev | - | - | E00-05 |
| [E00-07](E00-fundaciones/E00-07-backups-y-prueba-de-restauracion.md) | Backups y prueba de restauración | Debe | S | draft | dev | - | - | E00-05 |
| [E00-08](E00-fundaciones/E00-08-observabilidad-minima.md) | Observabilidad mínima | Debería | S | draft | dev | - | - | E00-05 |
| [E00-09](E00-fundaciones/E00-09-almacenamiento-de-archivos-con-urls-firmadas.md) | Almacenamiento de archivos con URLs firmadas | Debe | M | draft | dev | - | - | E00-01 |
| [E00-10](E00-fundaciones/E00-10-envio-de-mail-transaccional.md) | Envío de mail transaccional | Debe | S | draft | dev | D-009 | - | E00-01 |
| [E00-11](E00-fundaciones/E00-11-jobs-programados.md) | Jobs programados | Debe | S | draft | dev | - | - | E00-01 |

## E01 Acceso, usuarios y roles

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E01-01](E01-acceso/E01-01-iniciar-sesion-con-correo-y-contrasena.md) | Iniciar sesión con correo y contraseña | Debe | S | done | admin, technician, owner | - | D-007 | E00-01 |
| [E01-02](E01-acceso/E01-02-mantener-y-cerrar-la-sesion.md) | Mantener y cerrar la sesión | Debe | S | done | admin, technician, owner | - | - | E01-01 |
| [E01-03](E01-acceso/E01-03-gestionar-usuarios.md) | Gestionar usuarios | Debe | M | done | admin, owner | - | - | E01-04 |
| [E01-04](E01-acceso/E01-04-autorizacion-por-rol-en-la-api.md) | Autorización por rol en la API | Debe | M | done | admin, technician, owner | - | - | E01-01, E00-04 |
| [E01-05](E01-acceso/E01-05-restablecer-la-contrasena-de-un-usuario.md) | Restablecer la contraseña de un usuario | Debería | S | draft | admin | - | - | E01-03 |
| [E01-06](E01-acceso/E01-06-bloqueo-temporal-por-intentos-fallidos.md) | Bloqueo temporal por intentos fallidos | Debería | S | draft | admin, technician, owner | - | - | E01-01 |

## E02 Catálogos

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E02-01](E02-catalogos/E02-01-gestionar-tipos-de-trabajo-y-tareas.md) | Gestionar tipos de trabajo y tareas | Debe | M | done | admin | - | D-003 | E01-04 |
| [E02-02](E02-catalogos/E02-02-gestionar-tipos-de-equipo.md) | Gestionar tipos de equipo | Debe | S | done | admin | - | D-003 | E01-04 |
| [E02-03](E02-catalogos/E02-03-gestionar-fallas-por-tipo-de-equipo.md) | Gestionar fallas por tipo de equipo | Debe | M | draft | admin | - | D-003 | E02-02 |
| [E02-04](E02-catalogos/E02-04-gestionar-reparaciones.md) | Gestionar reparaciones | Debe | S | draft | admin | - | D-003 | E02-02 |
| [E02-05](E02-catalogos/E02-05-gestionar-el-catalogo-de-repuestos.md) | Gestionar el catálogo de repuestos | Debe | M | draft | admin | - | D-003 | E01-04, E00-04 |
| [E02-06](E02-catalogos/E02-06-gestionar-la-lista-de-precios-de-repuestos.md) | Gestionar la lista de precios de repuestos | Debe | M | draft | admin | - | - | E02-05 |
| [E02-07](E02-catalogos/E02-07-promover-un-texto-de-otro-a-la-lista.md) | Promover un texto de "Otro" a la lista | Debería | M | draft | admin | - | - | E02-03, E02-04, E05-04 |
| [E02-08](E02-catalogos/E02-08-importar-y-exportar-catalogos-por-csv.md) | Importar y exportar catálogos por CSV | Podría | M | draft | admin | - | D-003 | E02-01, E02-05 |

## E03 Clientes y equipos

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E03-01](E03-clientes-equipos/E03-01-alta-y-edicion-de-clientes.md) | Alta y edición de clientes | Debe | M | draft | admin | - | - | E01-04 |
| [E03-02](E03-clientes-equipos/E03-02-domicilios-o-sitios-de-un-cliente.md) | Domicilios o sitios de un cliente | Debe | S | draft | admin | - | - | E03-01 |
| [E03-03](E03-clientes-equipos/E03-03-alta-y-edicion-de-equipos.md) | Alta y edición de equipos | Debe | M | draft | admin | D-002 | - | E03-02, E02-02 |
| [E03-04](E03-clientes-equipos/E03-04-ficha-de-cliente-con-historial.md) | Ficha de cliente con historial | Debe | M | draft | admin, owner | - | - | E03-01, E04-06 |
| [E03-05](E03-clientes-equipos/E03-05-ficha-de-equipo-con-historial-y-mediciones.md) | Ficha de equipo con historial y mediciones | Debe | M | draft | admin, owner | D-002 | - | E03-03, E04-06 |
| [E03-06](E03-clientes-equipos/E03-06-buscar-clientes-y-equipos.md) | Buscar clientes y equipos | Debe | S | draft | admin, owner | - | - | E03-01 |
| [E03-07](E03-clientes-equipos/E03-07-baja-logica-y-restauracion-de-clientes-y-equipos.md) | Baja lógica y restauración de clientes y equipos | Debería | S | draft | admin | - | - | E03-01, E03-03 |

## E04 Órdenes de trabajo (administración)

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E04-01](E04-ordenes/E04-01-maquina-de-estados-y-linea-de-tiempo-de-la-orden.md) | Máquina de estados y línea de tiempo de la orden | Debe | M | draft | admin | - | - | E00-01 |
| [E04-02](E04-ordenes/E04-02-crear-una-orden-de-trabajo.md) | Crear una orden de trabajo | Debe | M | draft | admin | - | - | E04-01, E03-02, E02-01 |
| [E04-03](E04-ordenes/E04-03-asignar-una-orden-a-un-tecnico.md) | Asignar una orden a un técnico | Debe | S | draft | admin | - | - | E04-02, E01-03 |
| [E04-04](E04-ordenes/E04-04-reasignar-o-desasignar-una-orden.md) | Reasignar o desasignar una orden | Debe | S | draft | admin | - | - | E04-03 |
| [E04-05](E04-ordenes/E04-05-panel-de-ordenes-por-estado.md) | Panel de órdenes por estado | Debe | M | draft | admin, owner | - | - | E04-01 |
| [E04-06](E04-ordenes/E04-06-detalle-de-la-orden-con-linea-de-tiempo.md) | Detalle de la orden con línea de tiempo | Debe | M | draft | admin, owner | - | - | E04-01, E00-09 |
| [E04-07](E04-ordenes/E04-07-cancelar-una-orden-con-motivo.md) | Cancelar una orden con motivo | Debe | S | draft | admin | - | - | E04-01 |
| [E04-08](E04-ordenes/E04-08-revisar-una-orden-terminada.md) | Revisar una orden terminada | Debe | M | draft | admin | - | D-005 | E04-06 |
| [E04-09](E04-ordenes/E04-09-registrar-la-factura-de-una-orden.md) | Registrar la factura de una orden | Debe | S | draft | admin | - | D-004 | E04-08 |
| [E04-10](E04-ordenes/E04-10-registrar-el-cobro-de-una-orden.md) | Registrar el cobro de una orden | Debe | S | draft | admin | - | - | E04-09 |
| [E04-11](E04-ordenes/E04-11-registrar-mano-de-obra-y-otros-cargos-de-una-orden.md) | Registrar mano de obra y otros cargos de una orden | Debería | M | draft | admin | - | - | E04-06, E00-04 |
| [E04-12](E04-ordenes/E04-12-asociar-un-equipo-a-la-orden.md) | Asociar un equipo a la orden | Debe | S | draft | admin | D-002 | - | E04-02, E03-03 |

## E05 App del técnico

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E05-01](E05-app-tecnico/E05-01-ver-mis-ordenes-asignadas.md) | Ver mis órdenes asignadas | Debe | S | draft | technician | - | - | E04-03, E01-04, E00-03 |
| [E05-02](E05-app-tecnico/E05-02-ver-el-detalle-de-una-orden-asignada.md) | Ver el detalle de una orden asignada | Debe | S | draft | technician | - | - | E05-01 |
| [E05-03](E05-app-tecnico/E05-03-iniciar-una-orden.md) | Iniciar una orden | Debe | S | draft | technician | - | - | E05-02, E04-01 |
| [E05-04](E05-app-tecnico/E05-04-cerrar-una-orden-con-falla-y-reparacion-de-listas.md) | Cerrar una orden con falla y reparación de listas | Debe | M | draft | technician | - | - | E05-03, E02-03, E02-04 |
| [E05-05](E05-app-tecnico/E05-05-registrar-repuestos-usados-con-cantidades-sin-precios.md) | Registrar repuestos usados con cantidades, sin precios | Debe | M | draft | technician | - | - | E05-04, E02-06, E08-04 |
| [E05-06](E05-app-tecnico/E05-06-agregar-foto-y-observacion-al-cierre.md) | Agregar foto y observación al cierre | Debe | M | draft | technician | - | - | E05-04, E00-09 |
| [E05-07](E05-app-tecnico/E05-07-firma-del-cliente-en-pantalla-con-nombre-y-dni.md) | Firma del cliente en pantalla con nombre y DNI | Debe | M | draft | technician | - | D-011 | E05-04, E00-09 |
| [E05-08](E05-app-tecnico/E05-08-elegir-el-resultado-del-trabajo.md) | Elegir el resultado del trabajo | Debe | M | draft | technician | - | - | E05-04, E04-01 |
| [E05-09](E05-app-tecnico/E05-09-guardar-mis-ordenes-en-el-celular-para-trabajar-sin-sen.md) | Guardar mis órdenes en el celular para trabajar sin señal | Debe | L | draft | technician | D-001 | - | E05-01, E00-03 |
| [E05-10](E05-app-tecnico/E05-10-cola-de-cierres-pendientes-de-sincronizar.md) | Cola de cierres pendientes de sincronizar | Debe | L | draft | technician | D-001 | - | E05-09, E05-12 |
| [E05-11](E05-app-tecnico/E05-11-ver-el-estado-de-sincronizacion-y-resolver-conflictos.md) | Ver el estado de sincronización y resolver conflictos | Debe | M | draft | technician, admin | D-001 | - | E05-10, E04-04 |
| [E05-12](E05-app-tecnico/E05-12-cierre-de-orden-idempotente.md) | Cierre de orden idempotente | Debe | S | draft | technician | - | - | E05-04, E04-01 |

## E06 Órdenes de taller

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E06-01](E06-taller/E06-01-crear-una-orden-de-taller-desde-la-oficina.md) | Crear una orden de taller desde la oficina | Debe | M | draft | admin | - | - | E04-02 |
| [E06-02](E06-taller/E06-02-convertir-una-orden-en-el-lugar-en-orden-de-taller.md) | Convertir una orden en el lugar en orden de taller | Debe | M | draft | technician, admin | - | - | E05-08, E06-01 |
| [E06-03](E06-taller/E06-03-asignar-cada-etapa-a-un-tecnico.md) | Asignar cada etapa a un técnico | Debe | S | draft | admin | - | - | E06-01, E04-03 |
| [E06-04](E06-taller/E06-04-registrar-el-retiro-del-equipo-con-firma-del-cliente.md) | Registrar el retiro del equipo con firma del cliente | Debe | M | draft | technician | - | - | E06-03, E05-07 |
| [E06-05](E06-taller/E06-05-registrar-el-trabajo-en-taller.md) | Registrar el trabajo en taller | Debe | M | draft | technician | - | - | E06-04, E05-05 |
| [E06-06](E06-taller/E06-06-registrar-la-devolucion-del-equipo-con-firma-del-client.md) | Registrar la devolución del equipo con firma del cliente | Debe | M | draft | technician | - | - | E06-05, E05-07 |
| [E06-07](E06-taller/E06-07-ver-que-equipos-estan-en-el-galpon-y-en-que-etapa.md) | Ver qué equipos están en el galpón y en qué etapa | Debe | S | draft | admin, owner | - | - | E06-04 |
| [E06-08](E06-taller/E06-08-estado-calculado-y-facturacion-unica-de-la-orden-de-tal.md) | Estado calculado y facturación única de la orden de taller | Debe | M | draft | admin | - | - | E06-06, E04-08 |

## E07 Mantenimiento preventivo

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E07-01](E07-mantenimiento/E07-01-gestionar-plantillas-de-checklist-por-frecuencia-y-tipo.md) | Gestionar plantillas de checklist por frecuencia y tipo de equipo | Debe | M | draft | admin | - | - | E02-02, E01-04 |
| [E07-02](E07-mantenimiento/E07-02-definir-mediciones-con-unidad-y-rango-esperado.md) | Definir mediciones con unidad y rango esperado | Debe | S | draft | admin | - | - | E07-01 |
| [E07-03](E07-mantenimiento/E07-03-gestionar-abonos-equipos-incluidos-y-frecuencia.md) | Gestionar abonos: equipos incluidos y frecuencia | Debe | M | draft | admin | D-002 | - | E03-03, E07-01 |
| [E07-04](E07-mantenimiento/E07-04-generar-las-ordenes-de-mantenimiento-cada-mes.md) | Generar las órdenes de mantenimiento cada mes | Debe | L | draft | admin | - | D-005 | E07-03, E00-11, E04-02 |
| [E07-05](E07-mantenimiento/E07-05-aprobar-en-bloque-las-ordenes-de-mantenimiento-generada.md) | Aprobar en bloque las órdenes de mantenimiento generadas | Debe | M | draft | admin | - | D-005 | E07-04, E04-07 |
| [E07-06](E07-mantenimiento/E07-06-completar-el-checklist-de-mantenimiento-en-la-app-del-t.md) | Completar el checklist de mantenimiento en la app del técnico | Debe | M | draft | technician | - | - | E07-04, E05-03 |
| [E07-07](E07-mantenimiento/E07-07-registrar-mediciones-y-marcar-las-que-estan-fuera-de-ra.md) | Registrar mediciones y marcar las que están fuera de rango | Debe | M | draft | technician | - | - | E07-06, E07-02 |
| [E07-08](E07-mantenimiento/E07-08-marcar-requiere-reparacion-desde-un-item-no-ok.md) | Marcar "requiere reparación" desde un ítem No OK | Debe | M | draft | technician | - | - | E07-06, E05-04 |
| [E07-09](E07-mantenimiento/E07-09-ver-la-evolucion-de-mediciones-de-un-equipo.md) | Ver la evolución de mediciones de un equipo | Debería | M | draft | admin, owner | D-002 | - | E07-07, E03-05 |

## E08 Stock de repuestos

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E08-01](E08-stock/E08-01-gestionar-depositos-y-camionetas.md) | Gestionar depósitos y camionetas | Debe | S | draft | admin | - | - | E01-04 |
| [E08-02](E08-stock/E08-02-registrar-el-ingreso-de-repuestos.md) | Registrar el ingreso de repuestos | Debe | S | draft | admin | - | - | E08-01, E02-05 |
| [E08-03](E08-stock/E08-03-transferir-repuestos-entre-ubicaciones.md) | Transferir repuestos entre ubicaciones | Debe | S | draft | admin | - | - | E08-02 |
| [E08-04](E08-stock/E08-04-descontar-stock-al-usar-repuestos-en-un-cierre.md) | Descontar stock al usar repuestos en un cierre | Debe | M | draft | technician | - | - | E08-03, E05-12, E02-06 |
| [E08-05](E08-stock/E08-05-consultar-stock-por-ubicacion-y-repuesto.md) | Consultar stock por ubicación y repuesto | Debe | S | draft | admin, technician, owner | - | - | E08-04 |
| [E08-06](E08-stock/E08-06-ajustar-stock-con-motivo.md) | Ajustar stock con motivo | Debería | S | draft | admin | - | - | E08-02 |
| [E08-07](E08-stock/E08-07-ver-el-historial-de-movimientos-de-un-repuesto.md) | Ver el historial de movimientos de un repuesto | Debería | S | draft | admin | - | - | E08-04 |
| [E08-08](E08-stock/E08-08-uso-de-repuestos-sin-stock-disponible.md) | Uso de repuestos sin stock disponible | Debería | S | draft | technician, admin | - | - | E08-04, E08-06 |

## E09 Comprobantes e informes

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E09-01](E09-comprobantes-informes/E09-01-generar-el-comprobante-pdf-de-retiro.md) | Generar el comprobante PDF de retiro | Debe | M | draft | admin | - | - | E06-04, E00-09 |
| [E09-02](E09-comprobantes-informes/E09-02-generar-el-comprobante-pdf-de-devolucion.md) | Generar el comprobante PDF de devolución | Debe | S | draft | admin | - | - | E06-06, E09-01 |
| [E09-03](E09-comprobantes-informes/E09-03-enviar-el-comprobante-al-cliente-por-mail.md) | Enviar el comprobante al cliente por mail | Debe | S | draft | admin | - | - | E09-01, E00-10 |
| [E09-04](E09-comprobantes-informes/E09-04-generar-el-informe-mensual-de-un-cliente.md) | Generar el informe mensual de un cliente | Debe | M | draft | admin | - | - | E04-06 |
| [E09-05](E09-comprobantes-informes/E09-05-enviar-el-informe-mensual-por-mail-a-cada-cliente.md) | Enviar el informe mensual por mail a cada cliente | Debe | M | draft | admin | - | - | E09-04, E00-10, E00-11, E03-01 |
| [E09-06](E09-comprobantes-informes/E09-06-previsualizar-y-reenviar-el-informe-mensual.md) | Previsualizar y reenviar el informe mensual | Podría | S | draft | admin | - | - | E09-05 |

## E10 Tablero de seguimiento

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E10-01](E10-tablero/E10-01-tablero-ordenes-por-estado.md) | Tablero: órdenes por estado | Debe | M | draft | owner, admin | - | - | E04-05 |
| [E10-02](E10-tablero/E10-02-tablero-trabajos-por-tecnico.md) | Tablero: trabajos por técnico | Debe | S | draft | owner, admin | - | - | E10-01 |
| [E10-03](E10-tablero/E10-03-tablero-tipos-de-reparacion-mas-comunes.md) | Tablero: tipos de reparación más comunes | Debe | S | draft | owner, admin | - | - | E10-01, E05-04 |
| [E10-04](E10-tablero/E10-04-tablero-avance-del-mantenimiento-preventivo.md) | Tablero: avance del mantenimiento preventivo | Debe | S | draft | owner, admin | - | - | E10-01, E07-04 |
| [E10-05](E10-tablero/E10-05-tablero-ordenes-terminadas-sin-facturar.md) | Tablero: órdenes terminadas sin facturar | Debe | S | draft | owner, admin | - | - | E10-01, E04-09 |
| [E10-06](E10-tablero/E10-06-tablero-repuestos-mas-usados.md) | Tablero: repuestos más usados | Debe | S | draft | owner, admin | - | - | E10-01, E08-04 |
| [E10-07](E10-tablero/E10-07-ver-el-tablero-desde-el-celular.md) | Ver el tablero desde el celular | Debe | S | draft | owner | - | - | E10-01 |
| [E10-08](E10-tablero/E10-08-tablero-filtros-por-cliente-tecnico-equipo-y-periodo.md) | Tablero: filtros por cliente, técnico, equipo y período | Debería | M | draft | owner, admin | - | - | E10-01 |

## E11 Migración y puesta en marcha

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E11-01](E11-migracion/E11-01-importar-clientes-desde-persat.md) | Importar clientes desde Persat | Debe | M | draft | admin | D-010 | - | E03-01, E11-05 |
| [E11-02](E11-migracion/E11-02-importar-equipos-desde-persat.md) | Importar equipos desde Persat | Debe | M | draft | admin | D-010, D-002 | - | E11-01, E03-03 |
| [E11-03](E11-migracion/E11-03-importar-el-historial-de-trabajos-de-persat.md) | Importar el historial de trabajos de Persat | Debe | L | draft | admin | D-010 | - | E11-02, E04-06 |
| [E11-04](E11-migracion/E11-04-informe-de-calidad-de-datos-de-la-importacion.md) | Informe de calidad de datos de la importación | Debería | M | draft | admin | D-010 | - | E11-01 |
| [E11-05](E11-migracion/E11-05-importacion-repetible-y-reversible.md) | Importación repetible y reversible | Debe | M | draft | admin | - | - | E00-01 |
| [E11-06](E11-migracion/E11-06-cargar-los-abonados-y-los-equipos-de-cada-abono.md) | Cargar los abonados y los equipos de cada abono | Debe | M | draft | admin | D-002 | - | E07-03, E11-02, E11-05 |
| [E11-07](E11-migracion/E11-07-guia-de-uso-y-practica-con-datos-de-prueba.md) | Guía de uso y práctica con datos de prueba | Debe | M | draft | admin, technician | - | - | E11-09 |
| [E11-08](E11-migracion/E11-08-criterios-de-salida-de-la-convivencia-con-persat.md) | Criterios de salida de la convivencia con Persat | Debería | S | draft | owner | - | - | E11-03 |
| [E11-09](E11-migracion/E11-09-datos-de-prueba-ficticios.md) | Datos de prueba ficticios | Debe | S | done | dev | - | - | E00-01 |

## E12 Transversal: auditoría, privacidad y calidad

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E12-01](E12-transversal/E12-01-auditoria-de-cambios.md) | Auditoría de cambios | Debe | M | draft | admin, owner | - | - | E00-01 |
| [E12-02](E12-transversal/E12-02-borrado-logico-y-restauracion.md) | Borrado lógico y restauración | Debe | S | draft | admin | - | - | E00-01 |
| [E12-03](E12-transversal/E12-03-errores-uniformes-y-en-espanol.md) | Errores uniformes y en español | Debe | S | draft | admin, technician, owner | - | - | E00-01 |
| [E12-04](E12-transversal/E12-04-proteccion-de-datos-personales.md) | Protección de datos personales | Debe | M | draft | owner | D-008 | - | E00-09 |
| [E12-05](E12-transversal/E12-05-paginacion-estandar-en-los-listados.md) | Paginación estándar en los listados | Debe | S | draft | admin, owner | - | - | E00-01 |
| [E12-06](E12-transversal/E12-06-uso-comodo-de-la-app-del-tecnico-a-la-intemperie.md) | Uso cómodo de la app del técnico a la intemperie | Debería | M | draft | technician | - | - | E00-03 |

## E99 Icebox: fuera de alcance por ahora

| ID | Historia | Prioridad | Tamaño | Estado | Roles | Bloq. | Supone | Depende de |
|---|---|---|---|---|---|---|---|---|
| [E99-01](E99-icebox/E99-01-codigo-qr-por-equipo.md) | Código QR por equipo | Podría | L | icebox | technician, admin | - | - | - |
| [E99-02](E99-icebox/E99-02-envio-del-informe-mensual-por-whatsapp.md) | Envío del informe mensual por WhatsApp | Podría | M | icebox | admin | - | - | - |
| [E99-03](E99-icebox/E99-03-agentes-de-ia-dentro-del-producto.md) | Agentes de IA dentro del producto | Podría | L | icebox | admin | - | - | - |
| [E99-04](E99-icebox/E99-04-portal-de-clientes.md) | Portal de clientes | Podría | L | icebox | admin | - | - | - |
| [E99-05](E99-icebox/E99-05-emision-de-factura-electronica.md) | Emisión de factura electrónica | Podría | L | icebox | admin | - | - | - |

## Historias bloqueadas por decisión

| Decisión | Estado | Historias bloqueadas |
|---|---|---|
| D-001 | Abierta | E05-09, E05-10, E05-11 |
| D-002 | Abierta | E03-03, E03-05, E04-12, E07-03, E07-09, E11-02, E11-06 |
| D-006 | Abierta | E00-05 |
| D-008 | Abierta | E12-04 |
| D-009 | Abierta | E00-10 |
| D-010 | Abierta | E11-01, E11-02, E11-03, E11-04 |
