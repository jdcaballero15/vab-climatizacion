import uuid
from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.api.schemas.client import ClientSiteTechnicianOut
from app.core.security import create_access_token
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from app.services import clients as clients_service
from tests.factories import make_user

TABLES = [User.__table__, Client.__table__, ClientSite.__table__, ClientContact.__table__]
CLIENTS_URL = "/admin/clients"
SITES_URL = "/admin/sites"
MAPS_PREFIX = "https://www.google.com/maps/search/?api=1&query="


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))
        await conn.execute(text("DROP TYPE IF EXISTS client_segment"))
        await conn.execute(text("DROP TYPE IF EXISTS tax_condition"))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([user])
    return user


@pytest.fixture
async def cliente(schema: None) -> Client:
    item = Client(number="1", name="Farmacia Ficticia")
    await _seed([item])
    return item


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _sites_url(client_id: object) -> str:
    return f"{CLIENTS_URL}/{client_id}/sites"


async def _crear(
    client: AsyncClient, admin: User, client_id: object, **payload: object
) -> dict[str, object]:
    response = await client.post(_sites_url(client_id), json=payload, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _code(response: Response) -> str:
    code: str = response.json()["detail"]["code"]
    return code


# Criterio 1: alcanza con la dirección; etiqueta y referencia son opcionales y queda activo.
async def test_agregar_domicilio_solo_con_direccion(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, address="  Av. Belgrano   123 ")

    assert creado["client_id"] == str(cliente.id)
    assert creado["address"] == "Av. Belgrano 123"
    assert creado["label"] is None
    assert creado["reference"] is None
    assert creado["is_active"] is True


async def test_agregar_domicilio_con_etiqueta_y_referencia(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(
            client,
            admin,
            cliente.id,
            label="Depósito",
            address="Calle Falsa 742, La Banda",
            reference="Portón verde, tocar timbre de atrás.",
        )

    assert creado["label"] == "Depósito"
    assert creado["reference"] == "Portón verde, tocar timbre de atrás."


# Criterio 2: se editan dirección, etiqueta y referencia; lo no enviado no cambia.
async def test_editar_domicilio(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, label="Sede", address="Calle 1")
        editado = await client.patch(
            f"{SITES_URL}/{creado['id']}",
            json={"address": "Calle 2", "reference": "Piso 3"},
            headers=_auth(admin),
        )
        consultado = await client.get(f"{SITES_URL}/{creado['id']}", headers=_auth(admin))

    assert editado.status_code == 200, editado.text
    assert editado.json()["address"] == "Calle 2"
    assert editado.json()["reference"] == "Piso 3"
    assert editado.json()["label"] == "Sede"
    assert consultado.json()["address"] == "Calle 2"


async def test_editar_borra_etiqueta_y_referencia_en_null(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(
            client, admin, cliente.id, label="Sede", address="Calle 1", reference="Piso 3"
        )
        editado = await client.patch(
            f"{SITES_URL}/{creado['id']}",
            json={"label": None, "reference": "   "},
            headers=_auth(admin),
        )

    assert editado.status_code == 200, editado.text
    assert editado.json()["label"] is None
    assert editado.json()["reference"] is None


# Criterio 3: el listado trae todos los domicilios del cliente, activos e inactivos.
async def test_listado_trae_activos_e_inactivos_del_cliente(admin: User, cliente: Client) -> None:
    otro = Client(number="2", name="Otro Cliente")
    await _seed([otro])
    async with _client() as client:
        uno = await _crear(client, admin, cliente.id, address="Calle 1")
        await _crear(client, admin, cliente.id, address="Calle 2")
        await _crear(client, admin, otro.id, address="Calle de otro")
        await client.patch(
            f"{SITES_URL}/{uno['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        listado = await client.get(_sites_url(cliente.id), headers=_auth(admin))

    assert listado.status_code == 200
    assert [(s["address"], s["is_active"]) for s in listado.json()] == [
        ("Calle 1", False),
        ("Calle 2", True),
    ]


# Criterio 4: se desactiva y se reactiva; no se borra.
async def test_desactivar_y_reactivar_domicilio(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, address="Calle 1")
        url = f"{SITES_URL}/{creado['id']}"
        desactivado = await client.patch(url, json={"is_active": False}, headers=_auth(admin))
        consultado = await client.get(url, headers=_auth(admin))
        reactivado = await client.patch(url, json={"is_active": True}, headers=_auth(admin))

    assert desactivado.json()["is_active"] is False
    assert consultado.status_code == 200
    assert reactivado.json()["is_active"] is True


async def test_no_hay_ruta_para_borrar_un_domicilio(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, address="Calle 1")
        response = await client.delete(f"{SITES_URL}/{creado['id']}", headers=_auth(admin))

    assert response.status_code == 405


# Criterio 5: enlace a una búsqueda de Google Maps con la dirección y "Santiago del Estero".
async def test_domicilio_trae_enlace_al_mapa(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, address="Av. Belgrano 123, La Banda")

    assert creado["map_url"] == (
        MAPS_PREFIX + "Av.%20Belgrano%20123%2C%20La%20Banda%2C%20Santiago%20del%20Estero"
    )


async def test_enlace_al_mapa_sigue_a_la_direccion_editada(admin: User, cliente: Client) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, address="Calle 1")
        editado = await client.patch(
            f"{SITES_URL}/{creado['id']}", json={"address": "Calle 2 & 3"}, headers=_auth(admin)
        )

    assert (
        editado.json()["map_url"]
        == MAPS_PREFIX + "Calle%202%20%26%203%2C%20Santiago%20del%20Estero"
    )


# Criterio 6: un contacto se asocia a un domicilio del mismo cliente; sin domicilio es general.
async def test_contacto_asociado_a_un_domicilio(admin: User, cliente: Client) -> None:
    async with _client() as client:
        sede = await _crear(client, admin, cliente.id, address="Calle 1")
        contactos_url = f"{CLIENTS_URL}/{cliente.id}/contacts"
        del_lugar = await client.post(
            contactos_url,
            json={"name": "Encargado", "client_site_id": sede["id"]},
            headers=_auth(admin),
        )
        general = await client.post(contactos_url, json={"name": "Dueño"}, headers=_auth(admin))
        desasociado = await client.patch(
            f"{contactos_url}/{del_lugar.json()['id']}",
            json={"client_site_id": None},
            headers=_auth(admin),
        )

    assert del_lugar.status_code == 201, del_lugar.text
    assert del_lugar.json()["client_site_id"] == sede["id"]
    assert general.json()["client_site_id"] is None
    assert desasociado.json()["client_site_id"] is None


async def test_contacto_con_domicilio_de_otro_cliente_o_inexistente_da_404(
    admin: User, cliente: Client
) -> None:
    otro = Client(number="2", name="Otro Cliente")
    await _seed([otro])
    async with _client() as client:
        ajena = await _crear(client, admin, otro.id, address="Calle de otro")
        contactos_url = f"{CLIENTS_URL}/{cliente.id}/contacts"
        con_ajena = await client.post(
            contactos_url,
            json={"name": "Ana", "client_site_id": ajena["id"]},
            headers=_auth(admin),
        )
        contacto = await client.post(contactos_url, json={"name": "Beto"}, headers=_auth(admin))
        con_inexistente = await client.patch(
            f"{contactos_url}/{contacto.json()['id']}",
            json={"client_site_id": str(uuid.uuid4())},
            headers=_auth(admin),
        )

    assert con_ajena.status_code == 404
    assert _code(con_ajena) == "site_not_found"
    assert con_inexistente.status_code == 404
    assert _code(con_inexistente) == "site_not_found"


# Criterio 7: el técnico ve dirección, referencia, mapa y nombres de los contactos de ese
# domicilio. Ni teléfonos ni emails, ni contactos de otros domicilios o generales.
async def test_vista_del_tecnico_solo_trae_lo_del_domicilio(admin: User, cliente: Client) -> None:
    async with _client() as client:
        sede = await _crear(client, admin, cliente.id, address="Calle 1", reference="Piso 2")
        otra = await _crear(client, admin, cliente.id, address="Calle 2")
        contactos_url = f"{CLIENTS_URL}/{cliente.id}/contacts"
        for payload in (
            {"name": "Encargado", "phone": "3855000000", "client_site_id": sede["id"]},
            {"phone": "3855111111", "client_site_id": sede["id"]},
            {"name": "De la otra", "client_site_id": otra["id"]},
            {"name": "General", "email": "general@ejemplo.com"},
        ):
            response = await client.post(contactos_url, json=payload, headers=_auth(admin))
            assert response.status_code == 201, response.text

    async with SessionLocal() as session:
        vista = await clients_service.get_site_for_technician(session, uuid.UUID(str(sede["id"])))

    assert vista == ClientSiteTechnicianOut(
        address="Calle 1",
        reference="Piso 2",
        map_url=MAPS_PREFIX + "Calle%201%2C%20Santiago%20del%20Estero",
        contact_names=["Encargado"],
    )


def test_esquema_del_tecnico_no_tiene_telefono_ni_email() -> None:
    assert set(ClientSiteTechnicianOut.model_fields) == {
        "address",
        "reference",
        "map_url",
        "contact_names",
    }


# Criterio 8: dirección vacía o de solo espacios se rechaza con 422.
async def test_direccion_vacia_se_rechaza(admin: User, cliente: Client) -> None:
    async with _client() as client:
        vacia = await client.post(
            _sites_url(cliente.id), json={"address": "   "}, headers=_auth(admin)
        )
        sin_direccion = await client.post(
            _sites_url(cliente.id), json={"label": "Sede"}, headers=_auth(admin)
        )
        creado = await _crear(client, admin, cliente.id, address="Calle 1")
        editada = await client.patch(
            f"{SITES_URL}/{creado['id']}", json={"address": ""}, headers=_auth(admin)
        )
        nula = await client.patch(
            f"{SITES_URL}/{creado['id']}", json={"address": None}, headers=_auth(admin)
        )

    assert [r.status_code for r in (vacia, sin_direccion, editada, nula)] == [422] * 4


# Criterio 9: cliente o domicilio inexistente da 404.
async def test_cliente_o_domicilio_inexistente_da_404(admin: User) -> None:
    async with _client() as client:
        sin_cliente = await client.post(
            _sites_url(uuid.uuid4()), json={"address": "Calle 1"}, headers=_auth(admin)
        )
        listado = await client.get(_sites_url(uuid.uuid4()), headers=_auth(admin))
        sin_domicilio = await client.get(f"{SITES_URL}/{uuid.uuid4()}", headers=_auth(admin))
        editar = await client.patch(
            f"{SITES_URL}/{uuid.uuid4()}", json={"address": "X"}, headers=_auth(admin)
        )

    assert _code(sin_cliente) == "client_not_found"
    assert _code(listado) == "client_not_found"
    assert _code(sin_domicilio) == "site_not_found"
    assert _code(editar) == "site_not_found"
    assert [r.status_code for r in (sin_cliente, listado, sin_domicilio, editar)] == [404] * 4


# Criterio 10: técnico y dirección reciben acceso denegado.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(
    schema: None, cliente: Client, role: UserRole
) -> None:
    usuario = make_user(email=f"{role.value}@ot-demo.com", role=role)
    sede = ClientSite(client_id=cliente.id, address="Calle 1")
    await _seed([usuario, sede])
    async with _client() as client:
        respuestas = [
            await client.get(_sites_url(cliente.id), headers=_auth(usuario)),
            await client.post(
                _sites_url(cliente.id), json={"address": "X"}, headers=_auth(usuario)
            ),
            await client.get(f"{SITES_URL}/{sede.id}", headers=_auth(usuario)),
            await client.patch(
                f"{SITES_URL}/{sede.id}", json={"address": "X"}, headers=_auth(usuario)
            ),
        ]

    assert [r.status_code for r in respuestas] == [403] * len(respuestas)
