# ADR: registros de decisiones de arquitectura

Un **ADR** documenta una decisión técnica importante: qué se decidió, por qué y qué se descartó.
Existe para que, dentro de seis meses o cuando un agente nuevo abra el repo, nadie tenga que
adivinar por qué las cosas son como son ni repetir una discusión ya cerrada.

## Cuándo escribir uno

Si la decisión **afecta a más de un área** o **es cara de revertir**, lleva ADR.

- Elegir framework, ORM, motor de base de datos o proveedor de hosting.
- Patrón de arquitectura y estructura de carpetas (incluida una carpeta nueva en la raíz).
- Esquema de autenticación y autorización, o visibilidad por rol.
- Estrategia de sincronización offline, reintentos e idempotencia.
- Tratamiento de datos personales (DNI, firmas) y retención.
- Cambiar una regla de `CLAUDE.md` o de `docs/code-standards.md`.

No hace falta ADR para: nombrar una función, agregar un test, corregir un bug.

## Cómo

1. Copiá [`0000-template.md`](0000-template.md) a `NNNN-titulo-en-kebab.md` con el próximo número libre.
2. Escribilo en estado `Propuesto` y abrí el PR.
3. Cuando se aprueba, pasa a `Aceptado`.

## Reglas

- **Un ADR aceptado no se edita ni se borra.** Si la decisión cambia, se escribe uno nuevo que lo
  *reemplaza* y se enlazan entre sí.
- Describe el **contexto y el porqué**, no el cómo. El cómo vive en el código.
- Si no podés nombrar al menos una alternativa descartada, probablemente no tomaste una decisión,
  juntaste una suposición.
- Una decisión que depende del cliente y todavía no se tomó **no es un ADR**: va en
  [`docs/domain/decisiones-pendientes.md`](../../domain/decisiones-pendientes.md).

## Índice

| ADR | Título | Estado |
|---|---|---|
| [0001](0001-monorepo.md) | Monorepo | Aceptado |
| [0002](0002-backend-fastapi-postgresql.md) | Backend con FastAPI y PostgreSQL | Aceptado |
| [0003](0003-pwa-offline-first-provisional.md) | PWA con modo offline (provisional, depende de D-001) | Reemplazado por 0009 |
| [0004](0004-hosting-paas-postgres-administrado.md) | Hosting PaaS con Postgres administrado | Aceptado |
| [0005](0005-reglas-de-datos.md) | Reglas de datos | Aceptado |
| [0006](0006-visibilidad-por-rol-en-la-api.md) | Visibilidad por rol en la API | Aceptado |
| [0007](0007-orden-unificada-con-etapas.md) | Orden unificada con etapas | Aceptado |
| [0008](0008-agentes-de-ia-en-el-repositorio.md) | Agentes de IA en el repositorio | Aceptado |
| [0009](0009-pwa-con-conexion-y-borrador-local.md) | App del técnico con conexión y borrador local del cierre | Propuesto |
| [0010](0010-sesion-persistente-con-cookie.md) | Sesión persistente con el refresh token en una cookie httpOnly | Propuesto |
