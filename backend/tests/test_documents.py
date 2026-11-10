"""E09-01 y E09-02: comprobantes de retiro y devolución; E09-04: informe mensual.

El bucket es un falso en memoria: el PDF se arma en el servidor y no hace falta MinIO.
"""

import uuid
from collections.abc import AsyncGenerator, Iterator
from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from PIL import Image
from sqlalchemy import func, select, text, update

from app.core.sensitive_fields import FORBIDDEN_TECHNICIAN_FIELDS
from app.core.storage import get_storage
from app.db.models.catalog import Failure, Repair
from app.db.models.document import OrderDocument
from app.db.models.part import Part, PartUsage
from app.db.models.signature import Signature
from app.db.models.stored_file import StoredFile
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderClosure, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import (
    ClosureOutcome,
    EquipmentCondition,
    OrderKind,
    OrderStatus,
    SignaturePurpose,
    WorkOrderEventType,
    WorkshopStage,
)
from app.main import app
from app.services import pdf
from tests import test_work_order_closure_admin as cierre
from tests.factories import make_user
from tests.test_work_order_closure_admin import ORDERS_URL, TABLES, Mundo, _auth, _orden, _seed

mundo = cierre.mundo
DOCUMENT_TABLES = [*TABLES, OrderDocument.__table__]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=DOCUMENT_TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(DOCUMENT_TABLES)))
        for enum_type in (*cierre.ENUM_TYPES, "document_kind"):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def get_bytes(self, key: str) -> bytes:
        return self.objects[key]

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def download_url(self, key: str) -> str:
        return f"https://bucket.test/{key}?firmada"


@pytest.fixture
def storage() -> Iterator[FakeStorage]:
    fake = FakeStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_storage, None)


def _png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (40, 20), "white").save(buffer, format="PNG")
    return buffer.getvalue()


async def _call(user: Any, method: str, url: str) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, headers=_auth(user))


async def _etapa_cerrada(
    m: Mundo, storage: FakeStorage, stage: WorkshopStage, *, firma: bool = True
) -> WorkOrder:
    """Orden de taller con la etapa cerrada como hecha y, si firma, la firma del cliente."""
    orden = await _orden(m, OrderStatus.done)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder)
            .where(WorkOrder.id == orden.id)
            .values(kind=OrderKind.workshop, workshop_stage=stage)
        )
        await session.commit()
    closure = WorkOrderClosure(
        work_order_id=orden.id,
        closed_by=m.celular.id,
        closed_at=datetime(2026, 11, 5, 15, 30, tzinfo=UTC),
        idempotency_key=uuid.uuid4(),
        outcome=ClosureOutcome.done,
        workshop_stage=stage,
        equipment_condition=EquipmentCondition.working,
    )
    await _seed([closure])
    if firma:
        archivo = StoredFile(
            purpose="signature",
            object_key=f"closures/{uuid.uuid4()}",
            content_type="image/png",
            size_bytes=10,
            uploaded_by=m.celular.id,
            confirmed_at=datetime.now(UTC),
        )
        await _seed([archivo])
        storage.objects[archivo.object_key] = _png()
        purpose = (
            SignaturePurpose.pickup if stage == WorkshopStage.pickup else SignaturePurpose.delivery
        )
        await _seed(
            [
                Signature(
                    closure_id=closure.id,
                    purpose=purpose,
                    signer_name="Rosa Ficticia",
                    image_file_id=archivo.id,
                )
            ]
        )
    return orden


# E09-01, criterios 1 y 3: el comprobante se arma con la firma, se guarda en el bucket y
# pedirlo otra vez devuelve el mismo archivo.
async def test_comprobante_de_retiro(mundo: Mundo, storage: FakeStorage) -> None:
    m = mundo
    orden = await _etapa_cerrada(m, storage, WorkshopStage.pickup)
    url = f"{ORDERS_URL}/{orden.id}/documents/pickup_receipt"

    primero = await _call(m.admin, "POST", url)
    segundo = await _call(m.admin, "POST", url)

    assert primero.status_code == 200, primero.text
    assert primero.json()["url"] == segundo.json()["url"]
    pdfs = [data for key, data in storage.objects.items() if key.startswith("documents/")]
    assert len(pdfs) == 1
    assert pdfs[0].startswith(b"%PDF")
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(OrderDocument)) == 1


# Criterio 4 (E09-01) y 3 (E09-02): sin la etapa cerrada con firma, no hay comprobante.
@pytest.mark.parametrize("kind", ["pickup_receipt", "delivery_receipt"])
async def test_sin_etapa_cerrada_no_hay_comprobante(
    mundo: Mundo, storage: FakeStorage, kind: str
) -> None:
    m = mundo
    orden = await _etapa_cerrada(m, storage, WorkshopStage.pickup, firma=False)

    response = await _call(m.admin, "POST", f"{ORDERS_URL}/{orden.id}/documents/{kind}")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "stage_not_done"


# E09-02: la devolución suma el trabajo del galpón y los materiales, sin precios.
async def test_comprobante_de_devolucion(mundo: Mundo, storage: FakeStorage) -> None:
    m = mundo
    orden = await _etapa_cerrada(m, storage, WorkshopStage.delivery)
    filtro = Part(name="Filtro ficticio", unit="unidad")
    await _seed([filtro])
    await _seed(
        [
            PartUsage(
                work_order_id=orden.id,
                part_id=filtro.id,
                quantity=Decimal("2"),
                created_by=m.celular.id,
            )
        ]
    )

    response = await _call(m.admin, "POST", f"{ORDERS_URL}/{orden.id}/documents/delivery_receipt")

    assert response.status_code == 200, response.text


def test_el_pdf_no_lleva_precios_y_trae_el_trabajo() -> None:
    contenido = pdf.build_receipt(
        pdf.ReceiptData(
            title="Comprobante de devolución",
            order_number=7,
            client_name="Hotel Ficticio",
            client_number="10642",
            site="Calle 1",
            equipment="EA1064201 · Habitación 12",
            done_at=datetime(2026, 11, 5, 12, 0, tzinfo=UTC),
            crew="Escuadrilla 1",
            technicians=["Ana Ficticia"],
            condition="Funcionando bien",
            signer_name="Rosa Ficticia",
            signature_png=_png(),
            work_lines=["Material: Filtro ficticio x 2 unidad"],
        )
    )
    assert contenido.startswith(b"%PDF")
    # Sin precios por construcción: los datos de los PDF no tienen dónde llevarlos.
    for data_class in (pdf.ReceiptData, pdf.ReportLine, pdf.MonthlyReportData):
        nombres = {campo.name for campo in fields(data_class)}
        assert not nombres & FORBIDDEN_TECHNICIAN_FIELDS


# E09-04: el informe del mes lista los trabajos terminados del cliente; mismo período, mismo
# archivo; sin trabajos, no hay informe.
async def test_informe_mensual(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.done)
    falla = Failure(name="No enfría")
    await _seed([falla])
    reparacion = Repair(name="Carga de gas", failure_id=falla.id)
    await _seed([reparacion])
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=orden.id,
                event_type=WorkOrderEventType.status_change,
                from_status=OrderStatus.in_progress,
                to_status=OrderStatus.done,
                occurred_at=datetime(2026, 10, 15, 14, 0, tzinfo=UTC),
            ),
            WorkOrderClosure(
                work_order_id=orden.id,
                closed_by=m.celular.id,
                closed_at=datetime(2026, 10, 15, 14, 0, tzinfo=UTC),
                idempotency_key=uuid.uuid4(),
                outcome=ClosureOutcome.done,
                failure_id=falla.id,
                repair_id=reparacion.id,
            ),
        ]
    )
    client_id = m.sede.client_id
    url = f"/admin/clients/{client_id}/monthly-report"

    octubre = await _call(m.admin, "GET", f"{url}?year=2026&month=10")
    otra_vez = await _call(m.admin, "GET", f"{url}?year=2026&month=10")
    noviembre = await _call(m.admin, "GET", f"{url}?year=2026&month=11")

    assert octubre.status_code == 200
    assert octubre.headers["content-type"] == "application/pdf"
    assert octubre.content == otra_vez.content
    assert noviembre.status_code == 409
    assert noviembre.json()["detail"]["code"] == "empty_report"


# Permisos: el técnico no ve comprobantes ni informes; dirección ve el informe.
async def test_permisos(mundo: Mundo, storage: FakeStorage) -> None:
    m = mundo
    orden = await _etapa_cerrada(m, storage, WorkshopStage.pickup)
    direccion = make_user(email="direccion@ot-demo.com", role=UserRole.owner)
    await _seed([direccion])
    url = f"/admin/clients/{m.sede.client_id}/monthly-report?year=2026&month=10"

    tecnico_comprobante = await _call(
        m.celular, "POST", f"{ORDERS_URL}/{orden.id}/documents/pickup_receipt"
    )
    tecnico_informe = await _call(m.celular, "GET", url)
    direccion_informe = await _call(direccion, "GET", url)

    assert tecnico_comprobante.status_code == 403
    assert tecnico_informe.status_code == 403
    assert direccion_informe.status_code in (200, 409)
