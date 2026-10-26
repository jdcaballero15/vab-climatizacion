---
id: E11-09
title: "Datos de prueba ficticios"
epic: E11
phase: 1
priority: must
status: done
roles: [dev]
size: S
areas: [backend, datos]
depends_on: [E00-01]
blocked_by: []
assumes: []
---

# E11-09 Datos de prueba ficticios

## Historia

**Como** equipo de desarrollo, **quiero** un generador de datos de prueba ficticios (clientes, equipos, órdenes, stock), **para** desarrollar, probar y capacitar sin usar datos reales.

## Criterios de aceptación

1. **Dado:** una base vacía. **Cuando:** corro el generador. **Entonces:** crea usuarios ficticios de cada rol (1 administración, 1 dirección y 4 técnicos).
2. **Dado:** los datos generados. **Cuando:** se revisan. **Entonces:** no contienen DNI, nombres ni direcciones reales.
3. **Dado:** el generador. **Cuando:** se ejecuta dos veces. **Entonces:** es repetible con una semilla fija.
4. **Dado:** una base que ya tiene datos. **Cuando:** corro el generador. **Entonces:** no escribe nada y avisa.
5. **Dado:** el entorno de producción o la contraseña de los usuarios sin definir. **Cuando:** corro el generador. **Entonces:** se niega a correr.

## Notas técnicas

- El criterio 1 original pedía también clientes, equipos, órdenes en todos los estados, repuestos y movimientos de stock. Esas entidades todavía no existen (E02, E03, E04 y E08 están en borrador), así que el generador arranca solo con usuarios y **cada historia que agregue una entidad suma su parte al generador**.
- Nombres de listas inventadas fijas, sin Faker: evita nombres que coincidan con personas reales y no agrega dependencias. Correos con el dominio `@ot-demo.com`, el mismo de los tests.
- La contraseña de los usuarios generados se pasa con `SEED_PASSWORD` (sin valor por defecto): el repo es público y una contraseña fija en el código quedaría expuesta si el generador se corre en un entorno accesible (por ejemplo, para capacitar en E11-07).
- Uso: `SEED_PASSWORD=... make seed`.

## Notas de implementación

- Caso de uso en `backend/app/services/demo_data.py` (`generate_demo_data`, `ensure_can_run`); punto de entrada en `backend/app/demo_data.py` (`python -m app.demo_data [--seed N]`), que es lo que corre `make seed`.
- Genera `admin@`, `direccion@` y `tecnico1@` a `tecnico4@ot-demo.com`. Los correos son fijos; la semilla (por defecto 1) decide los nombres, sin repetirlos.
- "Base vacía" hoy significa sin usuarios, incluidos los dados de baja. Cuando el generador sume entidades, el chequeo tiene que cubrirlas también.
- `SEED_PASSWORD` se agregó a `Settings` y a `.env.example` (vacía). El generador se niega a correr con `APP_ENV=production` o con una contraseña de menos de 8 caracteres, el mismo mínimo que el alta de usuarios.
- Tests en `backend/tests/test_demo_data.py`, uno o más por criterio.

