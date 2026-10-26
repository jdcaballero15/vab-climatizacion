---
id: E03-02
title: "Domicilios o sitios de un cliente"
epic: E03
phase: 1
priority: must
status: ready
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-01]
blocked_by: []
assumes: []
---

# E03-02 Domicilios o sitios de un cliente

## Historia

**Como** administración, **quiero** registrar uno o más domicilios o sedes por cliente, **para** saber a dónde ir y dónde está cada equipo.

## Criterios de aceptación

1. **Dado:** un cliente. **Cuando:** administración le agrega un domicilio con dirección y, si quiere, etiqueta (por ejemplo "Sede central" o "Depósito") y referencia (piso, departamento, cómo llegar). **Entonces:** queda activo y se ofrece al crear órdenes de ese cliente.
2. **Dado:** un domicilio. **Cuando:** administración edita la dirección, la etiqueta o la referencia. **Entonces:** el cambio se ve en las órdenes abiertas de ese domicilio y en sus equipos.
3. **Dado:** un cliente. **Cuando:** administración abre sus domicilios. **Entonces:** ve todos, activos e inactivos, con su etiqueta, dirección, referencia y cantidad de equipos.
4. **Dado:** un domicilio. **Cuando:** administración lo desactiva. **Entonces:** deja de ofrecerse para órdenes nuevas, conserva sus equipos y su historial, y se puede reactivar. No se borra.
5. **Dado:** un domicilio. **Cuando:** se muestra en la administración o en la app del técnico. **Entonces:** tiene un enlace al mapa: una búsqueda de Google Maps con la dirección y "Santiago del Estero".
6. **Dado:** un contacto del cliente. **Cuando:** administración lo asocia a un domicilio (por ejemplo, el encargado de mantenimiento de una sede). **Entonces:** queda como contacto de ese lugar. Un contacto sin domicilio es del cliente en general.
7. **Dado:** el técnico con una orden asignada. **Cuando:** la abre. **Entonces:** ve la dirección, la referencia, el enlace al mapa y el nombre de los contactos de ese domicilio. No ve teléfonos ni emails, ni nada de otros domicilios del cliente.
8. **Dado:** una dirección vacía o de solo espacios. **Cuando:** se intenta guardar. **Entonces:** se rechaza con 422.
9. **Dado:** un cliente o domicilio inexistente. **Cuando:** se intenta usar. **Entonces:** se rechaza con 404.
10. **Dado:** un técnico o dirección. **Cuando:** llama a la API de domicilios de administración. **Entonces:** recibe acceso denegado (403).

## Fuera de alcance

- Elegir el domicilio al crear la orden (se elige solo si el cliente tiene uno activo): E04-02.
- Mover un domicilio a otro cliente o unificar clientes: E03-08.
- Importar los domicilios desde Persat: E11-01 (un domicilio por cliente).
- Registro en la auditoría: E12-01.

## Decisiones tomadas en el refinamiento

Validadas con negocio el 2026-10-26:

- **Varios domicilios por cliente desde el primer día.** Pasa mucho (cadenas de farmacias, organismos públicos, sanatorios con varias sedes). Persat no lo soporta y cada sede está cargada como un cliente distinto. La migración las importa tal cual y no las unifica; unificar es E03-08.
- **La referencia va en el domicilio**, no en el cliente: es lo que el técnico necesita en la orden.
- **Enlace al mapa** con una búsqueda de Google Maps. En Android abre Google Maps, o Waze si el técnico lo eligió como predeterminado. La localidad está en el texto de la dirección.
- **El técnico ve el nombre del contacto del lugar, pero no el teléfono.** El criterio del cliente es darle al técnico el menor margen posible, y el teléfono le permitiría contactar al cliente por fuera de la empresa. Está pendiente de confirmar con el cliente.
- Los criterios originales se mantienen: el 1 queda ampliado, el 2 ("solo se puede desactivar") pasa al 4 y el 3 (el técnico solo ve su domicilio) pasa al 7. Tamaño de S a M.

## Notas técnicas

- Tabla `client_site`: `label` opcional, `address` obligatoria, `reference` opcional, `is_active`. `client_contact.client_site_id` opcional. Actualizar `data-model.dbml`.
- El enlace al mapa se arma en el backend (`map_url` en la respuesta) para que las dos apps muestren lo mismo: `https://www.google.com/maps/search/?api=1&query=` + dirección + `, Santiago del Estero`, codificado.
- Endpoints bajo `/admin/clients/{id}/sites` y `/admin/sites/{id}`, con `require_role(admin)`.
- El esquema del técnico (`*TechnicianOut`) incluye del domicilio solo dirección, referencia, `map_url` y nombres de contactos. Sumar el caso al test de contrato: ni teléfono ni email de contactos.

## Preguntas abiertas

- Para el cliente: ¿el técnico tiene que ver el teléfono del contacto del lugar? Por defecto, no.
