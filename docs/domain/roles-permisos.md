# Roles y permisos

## Roles

| Rol (`role`) | Quién | Cantidad esperada | Dispositivo |
|---|---|---|---|
| Administración (`admin`) | Personal de oficina | 2 | PC o tablet |
| Técnico (`technician`) | Usuario de una escuadrilla (D-013): lo usan las personas que salen ese día con ese celular | Uno por escuadrilla | Celular Android de la empresa |
| Dirección (`owner`) | Dueño de la empresa | 1 | Celular y PC, principalmente tablero |

## Matriz

| Recurso | Administración | Técnico | Dirección |
|---|---|---|---|
| Crear, editar y cancelar órdenes | Sí | No | No |
| Asignar y desasignar | Sí | No | No |
| Ver órdenes | Todas | Solo las asignadas a su escuadrilla | Todas (lectura) |
| Iniciar y cerrar una orden | No | Sí, las de su escuadrilla | No |
| Ver precios, mano de obra y totales | Sí | **Nunca** | Sí |
| Ver historial de clientes y equipos | Sí | **Nunca** | Sí |
| Ver datos del equipo y la tarea de su orden | Sí | Sí | Sí |
| Revisar, facturar y cobrar | Sí | No | No |
| Editar catálogos | Sí | No | No |
| Gestionar escuadrillas y técnicos | Sí | No | No |
| Editar plantillas de checklist | Sí | No | No |
| Aprobar mantenimiento en bloque | Sí | No | No |
| Ver y mover stock | Sí | Ver el de su camioneta (ver E08-01) | Ver |
| Usar repuestos en un cierre | No | Sí (sin ver precios) | No |
| Ver tablero | Sí | No | Sí |
| Gestionar usuarios | Sí | No | Sí |
| Ver auditoría | Sí | No | Sí |

## Reglas

1. Los permisos se hacen cumplir en la API, nunca solo en la interfaz (ver [ADR 0006](../architecture/adr/0006-visibilidad-por-rol-en-la-api.md)).
2. El usuario de una escuadrilla no puede acceder por ID a una orden que no está asignada a su escuadrilla.
3. Las personas de campo (técnicos) no tienen usuario: figuran en una lista y se tildan al cerrar cada orden (D-013).
4. Qué ve la escuadrilla de su orden: cliente, dirección, equipo, tarea, instrucciones y los catálogos para cerrar. Nada más.
5. Cada acción sensible queda en la auditoría con usuario y fecha.

*Matriz propuesta. Validar con negocio, en especial los permisos de Dirección y las dos personas de administración (¿mismos permisos?).*
