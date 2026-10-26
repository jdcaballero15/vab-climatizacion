---
id: E03-03
title: "Alta y edición de equipos"
epic: E03
phase: 1
priority: must
status: done
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-02, E02-02]
blocked_by: []
assumes: [D-002]
---

# E03-03 Alta y edición de equipos

## Historia

**Como** administración, **quiero** dar de alta y editar los equipos de un cliente, **para** tener el parque de equipos para asociar trabajos e historial.

## Criterios de aceptación

1. **Dado:** un cliente con un domicilio activo. **Cuando:** administración crea un equipo con domicilio, tipo de equipo y ubicación (por ejemplo "Habitación 12"). **Entonces:** queda asociado a ese domicilio del cliente. Marca, modelo, número de serie y observaciones son opcionales.
2. **Dado:** un equipo nuevo. **Cuando:** se guarda. **Entonces:** el sistema le genera el código interno: prefijo del tipo de equipo + dígitos del número de cliente + correlativo del equipo dentro del cliente, con mínimo 2 dígitos (por ejemplo `EA1064201`). El código no se puede escribir ni editar a mano.
3. **Dado:** un cliente que ya tiene 99 equipos. **Cuando:** se da de alta el siguiente. **Entonces:** el correlativo pasa a `100`, sin rellenar los anteriores.
4. **Dado:** un código generado que ya existe en cualquier cliente. **Cuando:** se guarda el equipo. **Entonces:** el sistema prueba el siguiente correlativo; nunca quedan dos equipos con el mismo código.
5. **Dado:** un equipo. **Cuando:** administración le cambia la ubicación, el domicilio (otro del mismo cliente), el tipo o los datos opcionales. **Entonces:** conserva su código y su historial.
6. **Dado:** un cliente. **Cuando:** administración abre sus equipos. **Entonces:** ve cada equipo con su ubicación y tipo primero, y después código, domicilio, marca y modelo. Puede filtrar por domicilio.
7. **Dado:** un cliente con domicilios. **Cuando:** administración abre sus domicilios. **Entonces:** cada uno muestra su cantidad de equipos (pendiente de E03-02, criterio 3).
8. **Dado:** un domicilio inactivo o un tipo de equipo inactivo. **Cuando:** se lo elige para un equipo nuevo o para mover uno. **Entonces:** se rechaza con 422. Los equipos que ya estaban ahí no cambian.
9. **Dado:** una ubicación vacía o de solo espacios, o un domicilio de otro cliente. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
10. **Dado:** un cliente, domicilio, tipo o equipo inexistente. **Cuando:** se intenta usar. **Entonces:** se rechaza con 404.
11. **Dado:** un técnico o dirección. **Cuando:** llama a la API de equipos de administración. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Dar de baja y restaurar un equipo: E03-07. En esta historia no hay borrado de ningún tipo.
- Pasar un equipo a otro cliente (sigue abierto en D-002) y unificar clientes: E03-08.
- Ficha del equipo con historial y mediciones: E03-05. Buscar equipos: E03-06.
- Que el técnico dé de alta un equipo desde la app (pregunta abierta en D-002).
- Siglas de sector en el código (como `FAB`), hasta que el cliente confirme qué son.
- Editar el prefijo de un tipo de equipo desde la pantalla de tipos.
- Importar los equipos de Persat: E11-02.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Un prefijo por tipo de equipo**: `EA` aire acondicionado, `EH` heladera comercial y heladera familiar, `EC` cámara de frío, `EF` freezer y `EO` otros. Un tipo nuevo creado desde la pantalla de tipos usa `EO` hasta que se le asigne uno.
- **Datos opcionales**: marca, modelo, número de serie de fábrica y observaciones. No se guardan potencia, subtipo ni gas refrigerante como campos propios; si hacen falta, van en observaciones.
- **Mudanzas**: un equipo puede pasar a otro domicilio del mismo cliente y cambiar de ubicación, conservando código e historial (D-002, punto 4).
- El correlativo es por cliente, sin importar el tipo ni el domicilio: el primer equipo de un cliente es `01` aunque sea `EA` o `EH`.
- Los criterios originales se mantienen: el 3 (baja lógica) pasa a E03-07 como fuera de alcance, el 4 queda en el 4, el 5 se amplía con el cambio de domicilio, el 6 pasa al 11 y el 7 pasa al 3. Se suman listado, cantidad por domicilio y validaciones.

## Notas técnicas

- Tabla `equipment` según `data-model.dbml` (D-002), más `notes` opcional. Todas las columnas de texto se guardan sin espacios sobrantes; un texto vacío es nulo.
- `equipment_type.code_prefix` (texto, opcional): la migración lo completa para los seis tipos iniciales según las decisiones de arriba. Sin prefijo, el código usa `EO`. Actualizar `data-model.dbml`.
- Dígitos del número de cliente: se toman solo los dígitos de `client.number` (`CLI-00123` da `00123`). Si el número no tiene dígitos, se usa el número sin separadores.
- Correlativo: cantidad de equipos del cliente, contando los dados de baja, más uno. Como los largos de los códigos son variables y los migrados no siguen el formato, la unicidad la garantiza el índice único de `internal_code`: si choca, se prueba el siguiente correlativo (mismo patrón que el número de cliente de E03-01).
- Endpoints bajo `/admin/clients/{id}/equipment` (listar con filtro `site_id`, crear) y `/admin/equipment/{id}` (consultar, editar), con `require_role(admin)`. El esquema de entrada rechaza `internal_code` (`extra="forbid"`).
- `equipment_count` en `SiteAdminOut` (E03-02): cuenta los equipos no dados de baja del domicilio.
- Errores con `{code, message}` en español: `site_not_found`, `site_inactive`, `equipment_type_not_found`, `equipment_type_inactive`, `equipment_not_found`.
- Web-admin: sección "Equipos" en la ficha del cliente, con filtro por domicilio y formulario de alta y edición. Si el PR pasa de unas 400 líneas, se divide en backend y web-admin.

## Preguntas abiertas

- Para el cliente (ya en D-002): ¿quién asigna hoy los códigos?, ¿hay etiquetas físicas en los equipos? y ¿el técnico tiene que poder dar de alta un equipo que no encuentra en la lista?

## Notas de implementación

Se entrega en dos PR: backend primero, web-admin después.

- Backend (PR 1): `/admin/clients/{id}/equipment` (listar con `site_id` opcional, crear) y `/admin/equipment/{id}` (consultar, editar), todos con `require_role(admin)`. No hay ruta de borrado. Migración `2ecd8961c92f`: crea `equipment` con índice único en `internal_code` y agrega `equipment_type.code_prefix`, cargado por nombre para los seis tipos iniciales.
- Código: prefijo del tipo (o `EO`), dígitos de `client.number` y correlativo con mínimo 2 dígitos. El correlativo parte de la cantidad de equipos del cliente, contando los dados de baja, más uno. Si el código ya existe (por ejemplo, uno migrado de Persat), se saltea al siguiente; si dos altas simultáneas chocan en el índice, se reintenta y, si no hay suerte, 409 `equipment_code_unavailable`.
- Al editar solo se valida lo que cambia: un equipo que ya está en un domicilio o tipo desactivado se sigue pudiendo editar, pero no se puede mover a uno desactivado. El código no se edita y cambiar el tipo no lo cambia.
- Errores: 404 `client_not_found`, `site_not_found`, `equipment_type_not_found`, `equipment_not_found`; 422 `site_of_another_client`, `site_inactive`, `equipment_type_inactive`.
- `equipment_count` en las respuestas de domicilios (E03-02), sin los equipos dados de baja.
- Listado ordenado por ubicación y código, sin los dados de baja.
- Web-admin (PR 2): sección "Equipos" en la ficha del cliente, con ubicación y tipo primero, después código, domicilio, marca y modelo; filtro por domicilio; alta y edición con mudanza. Se ofrecen solo domicilios y tipos activos (uno inactivo aparece si el equipo ya está ahí). Sin domicilio activo, el alta avisa que hace falta uno. Los domicilios muestran su cantidad de equipos. Probado en el navegador contra el backend real.
