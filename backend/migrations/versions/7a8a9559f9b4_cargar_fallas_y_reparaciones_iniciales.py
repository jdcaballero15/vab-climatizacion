"""cargar fallas y reparaciones iniciales

Revision ID: 7a8a9559f9b4
Revises: 154f870b70dc
Create Date: 2026-10-26

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a8a9559f9b4"
down_revision: str | None = "154f870b70dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lista inicial del cliente (E02-03 y E02-04). Va en la migración y no en make seed porque
# también tiene que existir en producción; después se edita desde la pantalla. La
# clasificación por tipo de equipo falta que la confirme el cliente. "Otros" no se carga:
# es la opción fija del cierre con observación obligatoria (E05-04).

GAS = "Falla del sistema de gas"
ELECTRICA = "Falla eléctrica o mecánica"
LIMPIEZA = "Revisión y limpieza"

# Las tres fallas son genéricas: valen para todos los tipos de equipo.
INITIAL_FAILURES = (GAS, ELECTRICA, LIMPIEZA)

AIRE = "Aire acondicionado"
CAMARA = "Cámara de frío"
COMERCIAL = "Heladera comercial"
FAMILIAR = "Heladera familiar"
FREEZER = "Freezer"

# (falla, reparación, tipos de equipo). Sin tipos es genérica; con varios, una fila por tipo.
INITIAL_REPAIRS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (GAS, "Cambio de virolas y carga de gas", ()),
    (GAS, "Cambio de robinete y carga de gas", ()),
    (GAS, "Reparación de evaporadora con nitrógeno", ()),
    (GAS, "Reparación de condensadora con nitrógeno", ()),
    (GAS, "Cambio de válvula inversora", (AIRE,)),
    (GAS, "Cambio de tuercas y carga de gas", ()),
    (GAS, "Cambio de aceite de motor y carga de gas", ()),
    (GAS, "Cambio de conexión de evaporadora y carga de gas", ()),
    (GAS, "Cambio de filtro de gas", ()),
    (GAS, "Cambio de capilar", (CAMARA, COMERCIAL, FAMILIAR, FREEZER)),
    (GAS, "Aislación de cañería de refrigeración", ()),
    (ELECTRICA, "Reparación de placa", ()),
    (ELECTRICA, "Cambio de placa", ()),
    (ELECTRICA, "Cambio de terminales eléctricos", ()),
    (ELECTRICA, "Cambio de contactor", ()),
    (ELECTRICA, "Cambio de llave térmica", ()),
    (ELECTRICA, "Cambio de toma 20 A", ()),
    (ELECTRICA, "Cambio de capacitor", ()),
    (ELECTRICA, "Reparación de interconexión", (AIRE,)),
    (ELECTRICA, "Cambio de sensor de ambiente", ()),
    (ELECTRICA, "Cambio de electroválvula", (CAMARA, COMERCIAL, FREEZER)),
    (ELECTRICA, "Programación de control remoto", (AIRE,)),
    (ELECTRICA, "Cambio de turbina", (AIRE,)),
    (ELECTRICA, "Cambio de forzador", ()),
    (ELECTRICA, "Reparación de forzador", ()),
    (ELECTRICA, "Cambio de compresor", ()),
    (ELECTRICA, "Cambio de aspas", ()),
    (ELECTRICA, "Cambio de rodamientos", ()),
    (ELECTRICA, "Cambio de swing", (AIRE,)),
    (ELECTRICA, "Cambio de luz interior", (COMERCIAL, FAMILIAR, CAMARA)),
    (ELECTRICA, "Cambio de combistato", (COMERCIAL, FAMILIAR, FREEZER)),
    (ELECTRICA, "Reparación de puerta o burlete", (COMERCIAL, FAMILIAR, CAMARA, FREEZER)),
    (LIMPIEZA, "Limpieza de filtros y bandeja de descarga", (AIRE,)),
    (LIMPIEZA, "Limpieza de condensadora sin retiro", ()),
    (LIMPIEZA, "Limpieza de condensadora con retiro", ()),
    (LIMPIEZA, "Limpieza de difusores", (AIRE,)),
)

failure_table = sa.table(
    "failure",
    sa.column("id", sa.Uuid()),
    sa.column("equipment_type_id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("is_active", sa.Boolean()),
)
repair_table = sa.table(
    "repair",
    sa.column("id", sa.Uuid()),
    sa.column("failure_id", sa.Uuid()),
    sa.column("equipment_type_id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("is_active", sa.Boolean()),
)


def upgrade() -> None:
    failure_ids = {name: uuid.uuid4() for name in INITIAL_FAILURES}
    op.bulk_insert(
        failure_table,
        [
            {"id": failure_id, "equipment_type_id": None, "name": name, "is_active": True}
            for name, failure_id in failure_ids.items()
        ],
    )

    type_ids = _equipment_type_ids()
    rows = []
    for failure, name, types in INITIAL_REPAIRS:
        for equipment_type in types or (None,):
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "failure_id": failure_ids[failure],
                    "equipment_type_id": type_ids[equipment_type] if equipment_type else None,
                    "name": name,
                    "is_active": True,
                }
            )
    op.bulk_insert(repair_table, rows)


def downgrade() -> None:
    # Borra solo lo que cargó esta migración. Si administración ya agregó reparaciones a
    # estas fallas, la clave foránea lo impide y el downgrade falla en vez de perder datos.
    repair_names = sorted({name for _, name, _ in INITIAL_REPAIRS})
    op.execute(repair_table.delete().where(repair_table.c.name.in_(repair_names)))
    op.execute(
        failure_table.delete().where(
            failure_table.c.name.in_(INITIAL_FAILURES),
            failure_table.c.equipment_type_id.is_(None),
        )
    )


def _equipment_type_ids() -> dict[str, uuid.UUID]:
    """Ids de los tipos que usa la lista. Falla si falta alguno, para no cargar datos a medias."""
    needed = {t for _, _, types in INITIAL_REPAIRS for t in types}
    result = op.get_bind().execute(
        sa.text("SELECT name, id FROM equipment_type WHERE name IN :names").bindparams(
            sa.bindparam("names", expanding=True)
        ),
        {"names": sorted(needed)},
    )
    found = {name: type_id for name, type_id in result}
    missing = needed - found.keys()
    if missing:
        raise RuntimeError(
            f"Faltan tipos de equipo para cargar las reparaciones: {sorted(missing)}"
        )
    return found
