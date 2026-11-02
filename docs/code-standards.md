# Estándares de código

Normativo. El resumen ejecutable está en [`CLAUDE.md`](../CLAUDE.md). Cada regla indica cómo se hace cumplir.

| Tema | Regla | Se hace cumplir con |
|---|---|---|
| Idioma | Historias, docs, textos de interfaz y mensajes de error en español. Código (clases, tablas, columnas) en inglés. Sin guion largo | hook `guard_edit`, `validate_stories.py` |
| Python | 3.12, tipado completo, `mypy --strict`, línea de 100 | CI `backend`, pre-commit |
| Estilo | `ruff` es la única fuente de verdad | CI, pre-commit |
| Tamaño | Funciones de hasta 50 líneas, archivos de hasta 400. Si no entra, el diseño está mal | revisión |
| Capas | `api -> services -> domain <- db`. Sin lógica de negocio en rutas | revisión y `qa-reviewer` |
| Errores | Excepciones propias del dominio. Respuesta `{code, message}` con mensaje en español. Nunca `except Exception: pass` | revisión |
| Dinero | `Decimal` y `NUMERIC` en la base. Nunca `float`. Redondeo explícito | revisión, test |
| Datos | Borrado lógico, precios y fechas en tablas de transacción, precio de repuesto estampado al aprobar la orden, stock por movimientos ([ADR 0005](architecture/adr/0005-reglas-de-datos.md)) | tests, revisión |
| Rol técnico | Esquemas `*TechnicianOut` sin precios, mano de obra ni historial ([ADR 0006](architecture/adr/0006-visibilidad-por-rol-en-la-api.md)) | test de contrato (E00-04) |
| Seguridad | Autorización en cada endpoint y test de acceso denegado. Sin secretos en el código. Entradas validadas | CI, gitleaks |
| Datos personales | Nada de DNI, firmas ni datos reales en código, tests, capturas ni logs. No se loguean datos personales | gitleaks, revisión |
| Llamadas externas | Timeout explícito, reintento con espera creciente y manejo de fallo. Escrituras con clave de idempotencia | revisión |
| Logs | Estructurados, nunca `print()`. Sin secretos ni datos personales | ruff |
| Migraciones | Alembic, reversibles, probadas hacia arriba y hacia abajo | CI, agente `db-migrations` |
| Tests | Cada criterio de aceptación tiene al menos un test. Base de datos real, no mocks. Un bug se arregla con un test que lo reproduce primero. Los tests no usan la red | CI |
| TypeScript | `strict: true`. Prohibido `any` y `@ts-ignore`. Sin lógica de negocio en el cliente: la API decide | ESLint, CI |
| Frontend técnico | Botones de 48 px o más, opciones predefinidas, casi sin texto libre | revisión |
| Commits y ramas | Conventional Commits. Ramas `feat/`, `fix/`, `docs/`, `chore/`... | hook `guard_bash`, job `conventions` |
| Reglas desactivadas | Prohibido apagar una regla para que pase el CI: ni `# noqa` genérico, ni `--no-verify`, ni excluir archivos del linter | hook, revisión |
| IA en el producto | Fuera de la Fase 1. Si se agrega: prompts versionados, salida validada contra un esquema, nunca una acción irreversible directo de un modelo, sin datos personales reales | ADR previo |
