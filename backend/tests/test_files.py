"""E00-09: archivos en el bucket con URLs firmadas.

Usa el bucket S3 compatible real (MinIO en local y en el CI), igual que la base: sin mocks.
"""

import asyncio
from collections.abc import AsyncGenerator, Sequence

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import create_access_token
from app.core.storage import build_storage
from app.db.models.stored_file import StoredFile
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [User.__table__, StoredFile.__table__]
JPEG = b"\xff\xd8\xff\xe0" + b"foto-ficticia" * 50


pytestmark = pytest.mark.usefixtures("bucket")


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


@pytest.fixture
async def users(schema: None) -> dict[str, User]:
    created = {
        "celular": make_user(email="esc1@ot-demo.com", role=UserRole.technician),
        "otro_celular": make_user(email="esc2@ot-demo.com", role=UserRole.technician),
        "admin": make_user(email="admin@ot-demo.com", role=UserRole.admin),
    }
    await _seed(list(created.values()))
    return created


async def _seed(users: Sequence[User]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(users))
        await session.commit()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


async def _request(
    client: AsyncClient, user: User, content_type: str = "image/jpeg", size: int = len(JPEG)
) -> httpx.Response:
    return await client.post(
        "/files",
        json={"purpose": "closure_photo", "content_type": content_type, "size_bytes": size},
        headers=_auth(user),
    )


async def _put(url: str, body: bytes, content_type: str = "image/jpeg") -> httpx.Response:
    async with httpx.AsyncClient() as bucket_client:
        return await bucket_client.put(url, content=body, headers={"Content-Type": content_type})


async def _uploaded(client: AsyncClient, user: User) -> str:
    """Pide, sube y confirma una foto. Devuelve el id."""
    pedido = (await _request(client, user)).json()
    assert (await _put(pedido["upload_url"], JPEG)).status_code == 200
    confirm = await client.post(f"/files/{pedido['file_id']}/confirm", headers=_auth(user))
    assert confirm.status_code == 200
    return str(pedido["file_id"])


# Criterios 1 y 2: URL firmada, subida directa al bucket y confirmación con lo declarado.
async def test_subir_y_confirmar_una_foto(users: dict[str, User]) -> None:
    async with _client() as client:
        pedido = await _request(client, users["celular"])
        assert pedido.status_code == 201
        body = pedido.json()
        assert body["expires_in"] == 300

        subida = await _put(body["upload_url"], JPEG)
        confirm = await client.post(
            f"/files/{body['file_id']}/confirm", headers=_auth(users["celular"])
        )

    assert subida.status_code == 200
    assert confirm.status_code == 200
    archivo = confirm.json()
    assert archivo["content_type"] == "image/jpeg"
    assert archivo["size_bytes"] == len(JPEG)
    assert archivo["confirmed_at"] is not None


# Criterio 2: confirmar dos veces no cambia nada (reintento de la PWA).
async def test_confirmar_dos_veces_es_idempotente(users: dict[str, User]) -> None:
    async with _client() as client:
        file_id = await _uploaded(client, users["celular"])
        otra = await client.post(f"/files/{file_id}/confirm", headers=_auth(users["celular"]))

    assert otra.status_code == 200


# Criterio 3: confirmar algo que no llegó al bucket se rechaza.
async def test_confirmar_sin_subir_da_422(users: dict[str, User]) -> None:
    async with _client() as client:
        pedido = (await _request(client, users["celular"])).json()
        confirm = await client.post(
            f"/files/{pedido['file_id']}/confirm", headers=_auth(users["celular"])
        )

    assert confirm.status_code == 422
    assert confirm.json()["detail"]["code"] == "upload_missing"


# Criterios 1 y 3: el bucket no acepta un archivo distinto del declarado.
async def test_el_bucket_rechaza_otro_tamano_u_otro_tipo(users: dict[str, User]) -> None:
    async with _client() as client:
        pedido = (await _request(client, users["celular"])).json()

    mas_grande = await _put(pedido["upload_url"], JPEG + b"de-mas")
    otro_tipo = await _put(pedido["upload_url"], JPEG, content_type="image/png")

    assert mas_grande.status_code == 403
    assert otro_tipo.status_code == 403


# Criterio 3: otro usuario no puede confirmar un archivo ajeno.
async def test_confirmar_un_archivo_ajeno_da_404(users: dict[str, User]) -> None:
    async with _client() as client:
        pedido = (await _request(client, users["celular"])).json()
        await _put(pedido["upload_url"], JPEG)
        confirm = await client.post(
            f"/files/{pedido['file_id']}/confirm", headers=_auth(users["otro_celular"])
        )

    assert confirm.status_code == 404


# Criterio 4: la administración descarga con una URL firmada que funciona.
async def test_la_administracion_descarga_con_url_firmada(users: dict[str, User]) -> None:
    async with _client() as client:
        file_id = await _uploaded(client, users["celular"])
        respuesta = await client.get(f"/files/{file_id}/download", headers=_auth(users["admin"]))

    assert respuesta.status_code == 200
    async with httpx.AsyncClient() as bucket_client:
        descarga = await bucket_client.get(respuesta.json()["download_url"])
    assert descarga.status_code == 200
    assert descarga.content == JPEG


# Criterio 4: otro técnico no obtiene URL; sin sesión, tampoco.
async def test_otro_tecnico_o_sin_sesion_no_obtiene_url(users: dict[str, User]) -> None:
    async with _client() as client:
        file_id = await _uploaded(client, users["celular"])
        ajeno = await client.get(f"/files/{file_id}/download", headers=_auth(users["otro_celular"]))
        sin_sesion = await client.get(f"/files/{file_id}/download")

    assert ajeno.status_code == 404
    assert "download_url" not in ajeno.text
    assert sin_sesion.status_code == 401


# Criterio 4: un archivo sin confirmar no se descarga.
async def test_archivo_sin_confirmar_no_se_descarga(users: dict[str, User]) -> None:
    async with _client() as client:
        pedido = (await _request(client, users["celular"])).json()
        respuesta = await client.get(
            f"/files/{pedido['file_id']}/download", headers=_auth(users["admin"])
        )

    assert respuesta.status_code == 404


# Criterio 5: la URL firmada deja de funcionar al vencer.
async def test_la_url_firmada_vence(users: dict[str, User]) -> None:
    async with _client() as client:
        file_id = await _uploaded(client, users["celular"])
    async with SessionLocal() as session:
        archivo = await session.get(StoredFile, file_id)
        assert archivo is not None
        key = archivo.object_key

    url = build_storage(ttl_seconds=1).download_url(key)
    await asyncio.sleep(2)
    async with httpx.AsyncClient() as bucket_client:
        vencida = await bucket_client.get(url)

    assert vencida.status_code == 403


# Criterio 6: tipo no permitido o archivo grande se rechazan sin URL.
@pytest.mark.parametrize(
    ("content_type", "size", "code", "field"),
    [
        ("application/pdf", 1000, "file_type_not_allowed", "content_type"),
        ("text/html", 1000, "file_type_not_allowed", "content_type"),
        ("image/jpeg", 5 * 1024 * 1024 + 1, "file_too_large", "size_bytes"),
    ],
)
async def test_tipo_o_tamano_no_permitido_da_422(
    users: dict[str, User], content_type: str, size: int, code: str, field: str
) -> None:
    async with _client() as client:
        respuesta = await _request(client, users["celular"], content_type=content_type, size=size)

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == {
        "code": code,
        "field": field,
        "message": respuesta.json()["detail"]["message"],
    }
    assert "upload_url" not in respuesta.text


# Criterio 7: el bucket es privado.
async def test_el_bucket_no_entrega_objetos_sin_firma(users: dict[str, User]) -> None:
    async with _client() as client:
        file_id = await _uploaded(client, users["celular"])
    async with SessionLocal() as session:
        archivo = await session.get(StoredFile, file_id)
        assert archivo is not None
        key = archivo.object_key

    settings = get_settings()
    async with httpx.AsyncClient() as bucket_client:
        directo = await bucket_client.get(f"{settings.s3_endpoint_url}/{settings.s3_bucket}/{key}")

    assert directo.status_code == 403
