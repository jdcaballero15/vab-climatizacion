# Backend

API del sistema de órdenes de trabajo. Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic y PostgreSQL.

## Comandos

```bash
pip install -e ".[dev]"
pytest                 # tests
ruff check . && ruff format --check .
mypy app
uvicorn app.main:app --reload
```

Con Docker: `make up` en la raíz del repo.

## Capas

Dependencias permitidas, siempre hacia abajo:

```
api  ->  services  ->  domain  <-  db
```

| Carpeta | Responsabilidad | No debe |
|---|---|---|
| `app/api/` | Rutas HTTP, validación de entrada, esquemas de respuesta por rol, autorización | Contener reglas de negocio ni SQL |
| `app/services/` | Casos de uso (asignar orden, cerrar orden, generar mantenimiento). Una transacción por caso de uso | Conocer FastAPI |
| `app/domain/` | Entidades, estados, reglas puras (máquina de estados de la OT) | Importar SQLAlchemy ni FastAPI |
| `app/db/` | Modelos SQLAlchemy, repositorios, migraciones | Contener reglas de negocio |
| `app/core/` | Configuración, seguridad, logging, errores | Depender de otras capas |

Estas carpetas se crean con la primera historia que las necesite. Hoy existen `api/`, `core/`, `db/`, `domain/` y `services/`.

## Convenciones

- **Esquemas por rol**: cada recurso con datos sensibles tiene un esquema para administración (`OrderAdminOut`) y otro para técnico (`OrderTechnicianOut`) que no contiene campos de precio, mano de obra ni historial. Hay un test de contrato que recorre los esquemas del técnico y falla si aparece un campo prohibido.
- **Autorización por dependencia**: cada ruta declara el rol requerido con una dependencia (`require_role(...)`). No se confía en la interfaz.
- **Borrado lógico**: todo repositorio filtra `deleted_at IS NULL` por defecto. No existe `DELETE`.
- **Idempotencia**: los endpoints que usa la PWA offline (cerrar orden, subir foto, firmar) aceptan una clave de idempotencia generada por el cliente.
- **Errores**: formato único `{ "code": "...", "message": "..." }`, mensajes en español para el usuario.
- **Migraciones**: `alembic revision --autogenerate -m "..."`, revisadas a mano, siempre con `downgrade`.
- **Tests**: base de datos real (Postgres del CI), no mocks de la base. Datos ficticios con fábricas.
