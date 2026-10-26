---
id: E03-01
title: "Alta y edición de clientes"
epic: E03
phase: 1
priority: must
status: ready
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E01-04]
blocked_by: []
assumes: [D-002]
---

# E03-01 Alta y edición de clientes

## Historia

**Como** administración, **quiero** dar de alta y editar clientes con sus datos de contacto, **para** tener a cada cliente identificado y asociarle todos sus trabajos.

## Criterios de aceptación

1. **Dado:** administración. **Cuando:** crea un cliente con nombre. **Entonces:** queda activo, disponible para crear órdenes, con el segmento "Sin clasificar" si no se eligió otro. El resto de los datos es opcional.
2. **Dado:** un cliente nuevo. **Cuando:** se guarda. **Entonces:** el sistema le asigna el número de cliente: el siguiente al mayor de la serie numérica (los números con letras, como `CLI-00123`, no cuentan). El número no se puede escribir ni editar a mano.
3. **Dado:** un cliente. **Cuando:** administración edita nombre, segmento, CUIT o DNI, condición fiscal u observaciones. **Entonces:** el cambio se guarda y se ve en el listado y la ficha.
4. **Dado:** un cliente. **Cuando:** administración le agrega uno o más contactos con nombre, teléfono o email (al menos uno de los tres). **Entonces:** quedan asociados al cliente, y uno o más pueden marcarse para recibir el informe mensual.
5. **Dado:** un contacto marcado para recibir el informe mensual. **Cuando:** no tiene email. **Entonces:** se rechaza con 422 y un mensaje claro.
6. **Dado:** un email con formato inválido. **Cuando:** se guarda un contacto. **Entonces:** se rechaza con 422.
7. **Dado:** un cliente con nombre muy parecido a otro (sin distinguir mayúsculas, acentos ni espacios de más). **Cuando:** se guarda. **Entonces:** el sistema advierte del posible duplicado y deja confirmar o cancelar. No lo rechaza.
8. **Dado:** un número de cliente que ya existe. **Cuando:** se guarda un cliente con ese número (por ejemplo, en la importación). **Entonces:** se rechaza con 409.
9. **Dado:** un nombre vacío o de solo espacios. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
10. **Dado:** administración. **Cuando:** abre el listado de clientes. **Entonces:** ve número, nombre y segmento, paginado, y puede filtrar por segmento.
11. **Dado:** un técnico o dirección. **Cuando:** llama a la API de clientes de administración. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Domicilios del cliente, con su referencia y el enlace al mapa: E03-02.
- Unificar dos clientes (por ejemplo, sedes que en Persat están cargadas como clientes distintos): E03-08.
- Búsqueda de clientes: E03-06. Ficha con historial: E03-04.
- Baja lógica y restauración: E03-07. Registro en la auditoría: E12-01 (el criterio original de auditoría pasa ahí).
- Importación desde Persat: E11-01.
- Coordenadas, horario de jornada, tiempo de servicio, grupo, altura, localidad y provincia de Persat: no entran (ver Decisiones).

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26, con los datos de los 637 clientes de la exportación de Persat:

- **El contacto deja de ser obligatorio.** El criterio original pedía al menos un contacto, pero en Persat casi ningún cliente tiene nombre de contacto (11), teléfono (5) o email (1). Se cargan de a poco porque hacen falta para avisos e informes.
- **Número de cliente** (`client.number`, `D-002`): texto único, porque Persat mezcla una serie numérica y una serie `CLI-`. Lo asigna el sistema y no se edita, porque forma parte del código de los equipos.
- **Segmento** (desde "Tipo" de Persat): opcional, "Sin clasificar" por defecto. Valores: particular, comercio, estado, sanatorio o clínica, hotel, sin clasificar. Hoy el 81 % está sin clasificar; administración lo va completando. Sirve para filtrar y para el tablero.
- **Condición fiscal**: campo opcional nuevo (consumidor final, responsable inscripto, monotributo), útil para facturar. En Persat venía mezclada en "Descripción".
- **La referencia (piso, departamento, referencias de ubicación) va en el domicilio, no en el cliente** (E03-02): es lo que el técnico necesita en la orden. De la "Descripción" de Persat, el cliente se queda solo con el CUIT y la condición fiscal.
- **No entran**: coordenadas (el 36 % son inválidas, se ubica por la dirección), horario de jornada y tiempo de servicio (campos de ruteo de Persat que no se usan), grupo (duplica a "Tipo"), altura, localidad y provincia (la localidad queda en el texto de la dirección).
- El criterio de auditoría pasa a E12-01, como en los catálogos.

## Notas técnicas

- Unos 640 clientes y creciendo (637 en la exportación del 2026-10-08, 632 después de la limpieza). Con equipos cargados, 55.
- Tabla `client`: `number` (texto, único, no nulo), `name`, `segment` (enum `client_segment`, default `unclassified`), `tax_id` (CUIT o DNI, opcional), `tax_condition` (enum `tax_condition`, opcional), `notes`. Tabla `client_contact` (ya está en el modelo). Actualizar `data-model.dbml` si cambia algo.
- Número siguiente: el mayor de los números solo dígitos más uno. La unicidad la garantiza el índice único; si dos altas simultáneas chocan, se reintenta con el siguiente.
- CUIT o DNI, teléfono y email son datos personales (ver `SECURITY.md`): no se loguean y no van en el esquema del técnico.
- Endpoints bajo `/admin/clients` y `/admin/clients/{id}/contacts`, con `require_role(admin)`. Errores con `{code, message}` en español (`client_number_already_exists`, `client_not_found`). La advertencia de duplicado es una respuesta aparte que no impide guardar (por ejemplo, un endpoint de verificación o un campo `possible_duplicates` en la respuesta).
- Paginación según E12-05 si ya existe; si no, el mismo formato que los listados actuales.
- Si el PR pasa de unas 400 líneas, se divide en backend y web-admin.
