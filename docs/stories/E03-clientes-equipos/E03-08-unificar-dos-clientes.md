---
id: E03-08
title: "Unificar dos clientes"
epic: E03
phase: 2
priority: should
status: done
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

## Fuera de alcance

- Detectar automáticamente qué clientes unificar.
- Separar un cliente en dos.

## Decisiones (Gonza, 2026-11-10)

- El que se va queda dado de baja con su número; los códigos de sus equipos no cambian.
- No se puede restaurar un cliente unificado.

## Hecho

- `GET /admin/clients/{id}/merge-preview?into_client_id=...` cuenta domicilios, equipos, contactos y órdenes que pasarían; `POST /admin/clients/{id}/merge` los mueve (los equipos y sus planes siguen a su domicilio) y da de baja al que se va con `client.merged_into_id`.
- Las dos fichas registran la unificación en `audit_event`.
- web-admin: "Unificar en otro cliente" en la ficha: se elige el que queda, se ve qué pasa y se confirma.
