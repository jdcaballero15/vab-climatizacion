---
id: E03-08
title: "Unificar dos clientes"
epic: E03
phase: 2
priority: should
status: draft
roles: [admin]
size: M
areas: [backend, web-admin]
depends_on: [E03-02, E03-03, E03-07]
blocked_by: []
assumes: [D-002]
---

# E03-08 Unificar dos clientes

## Historia

**Como** administración, **quiero** unificar dos clientes que en realidad son el mismo, **para** que sus sedes, equipos e historial queden juntos bajo un solo cliente.

## Criterios de aceptación

1. **Dado:** dos clientes. **Cuando:** administración unifica uno (el que se va) en el otro (el que queda). **Entonces:** los domicilios, contactos, equipos, órdenes y abonos del que se va pasan al que queda, y el que se va queda dado de baja (borrado lógico).
2. **Dado:** la unificación. **Cuando:** se mueven los equipos. **Entonces:** conservan su código interno y su historial (`D-002`).
3. **Dado:** el cliente dado de baja. **Cuando:** se consulta. **Entonces:** indica en qué cliente se unificó.
4. **Dado:** una unificación. **Cuando:** se confirma. **Entonces:** antes de aplicarla se muestra qué se va a mover y hay que confirmarla.
5. **Dado:** un técnico o dirección. **Cuando:** intenta unificar clientes. **Entonces:** recibe acceso denegado (403).

## Notas técnicas

- Hace falta porque la migración importa tal cual los registros de Persat, y Persat no admite varios domicilios: muchas sedes de un mismo cliente (cadenas de farmacias, organismos públicos, sanatorios) están cargadas como clientes distintos. Unificar después es fácil; separar es difícil.
- Prevista para la versión 1.1.

## Preguntas abiertas

- Respondida en parte (cliente, 2026-10-28): depende del CUIT. Las sucursales con el mismo CUIT son un cliente con varios domicilios (se pueden unificar); las que tienen otro CUIT son clientes distintos. El Poder Judicial lo quiere cargar **por obra**, para distinguir cada una.
- Respondida (Gonza, 2026-10-28): en el Poder Judicial cada obra es un **domicilio** del mismo cliente, y se factura por obra. La facturación por domicilio va con D-004 (E04-09).
- ¿Qué pasa con el número de cliente del que se va? Los códigos de sus equipos lo llevan y no cambian; el número queda en el cliente dado de baja.

## Fuera de alcance

- Detectar automáticamente qué clientes unificar.
- Separar un cliente en dos.
