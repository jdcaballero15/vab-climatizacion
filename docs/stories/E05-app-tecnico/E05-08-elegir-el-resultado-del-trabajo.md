---
id: E05-08
title: "Elegir el resultado del trabajo"
epic: E05
phase: 1
priority: must
status: draft
roles: [technician]
size: M
areas: [backend, pwa]
depends_on: [E05-04, E04-01]
blocked_by: []
assumes: []
---

# E05-08 Elegir el resultado del trabajo

## Historia

**Como** técnico, **quiero** indicar si el equipo quedó funcionando y, si no, elegir entre "requiere retiro" y "requiere otra visita", **para** que la oficina sepa cómo seguir y se pueda medir qué se rompe más.

## Criterios de aceptación

1. **Dado:** un cierre. **Cuando:** marco que el equipo quedó funcionando. **Entonces:** la orden pasa a `Terminada` al enviarlo.
2. **Dado:** un cierre. **Cuando:** marco que el equipo no quedó funcionando. **Entonces:** debo elegir "requiere retiro" o "requiere otra visita" antes de enviar.
3. **Dado:** "requiere retiro". **Cuando:** envío el cierre. **Entonces:** la misma orden se convierte en orden de taller (ver E06-02).
4. **Dado:** "requiere otra visita". **Cuando:** envío el cierre. **Entonces:** la orden vuelve a `Pendiente` con lo registrado y el motivo visible para administración.
5. **Dado:** un cierre enviado. **Cuando:** administración lo ve. **Entonces:** la falla y la reparación quedan registradas por separado.

## Preguntas abiertas

Diferencias con el prototipo del cliente (2026-10-26), a revisar antes de pasar a `ready`:

- El prototipo permite cerrar como **"No realizada"** (cliente ausente o sin acceso, falta repuesto o herramienta, el equipo no tiene arreglo). La máquina de estados no tiene ese estado: hoy sería "requiere otra visita". ¿Hace falta un resultado o un estado propio?
- El prototipo separa **cómo quedó el equipo** (funcionando bien, con observaciones, no funciona) del **resultado**. Acá es solo "funcionando, sí o no".
