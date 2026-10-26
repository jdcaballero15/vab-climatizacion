from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.api.schemas.client import ClientCreate
from app.core.security import create_access_token
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from app.services import clients as clients_service
from tests.factories import make_user

TABLES = [User.__table__, Client.__table__, ClientSite.__table__, ClientContact.__table__]
URL = "/admin/clients"


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


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _crear(client: AsyncClient, admin: User, **payload: object) -> dict[str, object]:
    response = await client.post(URL, json=payload, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _code(response: Response) -> str:
    code: str = response.json()["detail"]["code"]
    return code


# Criterio 1: alcanza con el nombre; queda activo y "Sin clasificar" si no se eligió segmento.
async def test_crear_cliente_solo_con_nombre(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="  Panadería   El Trigal ")

    assert creado["name"] == "Panadería El Trigal"
    assert creado["segment"] == "unclassified"
    assert creado["tax_id"] is None
    assert creado["tax_condition"] is None
    assert creado["notes"] is None


async def test_crear_cliente_con_todos_los_datos(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(
            client,
            admin,
            name="Hotel Ficticio",
            segment="hotel",
            tax_id="20-12345678-9",
            tax_condition="registered_taxpayer",
            notes="Atender por la entrada de servicio.",
        )

    assert creado["segment"] == "hotel"
    assert creado["tax_id"] == "20-12345678-9"
    assert creado["tax_condition"] == "registered_taxpayer"
    assert creado["notes"] == "Atender por la entrada de servicio."


# Criterio 2: el número es el siguiente al mayor de los solo dígitos; los que tienen letras no
# cuentan. Con la base vacía arranca en 1.
async def test_numero_con_base_vacia_arranca_en_1(admin: User) -> None:
    async with _client() as client:
        primero = await _crear(client, admin, name="Cliente Uno")
        segundo = await _crear(client, admin, name="Cliente Dos")

    assert primero["number"] == "1"
    assert segundo["number"] == "2"


async def test_numero_sigue_la_serie_numerica_e_ignora_los_que_tienen_letras(admin: User) -> None:
    await _seed(
        [
            Client(number="10642", name="Migrado Uno"),
            Client(number="9999", name="Migrado Dos"),
            Client(number="CLI-99999", name="Migrado Tres"),
        ]
    )
    async with _client() as client:
        creado = await _crear(client, admin, name="Cliente Nuevo")

    assert creado["number"] == "10643"


async def test_numero_no_reusa_el_de_un_cliente_dado_de_baja(admin: User) -> None:
    from datetime import UTC, datetime

    await _seed([Client(number="50", name="Dado de baja", deleted_at=datetime.now(UTC))])
    async with _client() as client:
        creado = await _crear(client, admin, name="Cliente Nuevo")

    assert creado["number"] == "51"


async def test_numero_no_se_puede_mandar_al_crear_ni_editar(admin: User) -> None:
    async with _client() as client:
        crear = await client.post(
            URL, json={"name": "Con número", "number": "777"}, headers=_auth(admin)
        )
        creado = await _crear(client, admin, name="Sin número")
        editar = await client.patch(
            f"{URL}/{creado['id']}", json={"number": "777"}, headers=_auth(admin)
        )

    assert crear.status_code == 422
    assert editar.status_code == 422


# Criterio 3: se editan nombre, segmento, CUIT o DNI, condición fiscal y observaciones.
async def test_editar_cliente(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Comercio Viejo", tax_id="20111111112")
        editado = await client.patch(
            f"{URL}/{creado['id']}",
            json={
                "name": "Comercio Nuevo",
                "segment": "business",
                "tax_condition": "monotributo",
                "tax_id": None,
                "notes": "Cambió de dueño.",
            },
            headers=_auth(admin),
        )
        consultado = await client.get(f"{URL}/{creado['id']}", headers=_auth(admin))
        listado = await client.get(URL, headers=_auth(admin))

    assert editado.status_code == 200, editado.text
    body = consultado.json()
    assert body["name"] == "Comercio Nuevo"
    assert body["segment"] == "business"
    assert body["tax_condition"] == "monotributo"
    assert body["tax_id"] is None
    assert body["notes"] == "Cambió de dueño."
    assert body["number"] == creado["number"]
    assert [c["name"] for c in listado.json()["items"]] == ["Comercio Nuevo"]


async def test_editar_sin_mandar_campos_no_borra_los_demas(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Estudio", tax_id="20111111112", notes="Nota")
        editado = await client.patch(
            f"{URL}/{creado['id']}", json={"segment": "business"}, headers=_auth(admin)
        )

    assert editado.json()["tax_id"] == "20111111112"
    assert editado.json()["notes"] == "Nota"


async def test_editar_cliente_inexistente_da_404(admin: User) -> None:
    async with _client() as client:
        response = await client.patch(
            f"{URL}/00000000-0000-0000-0000-000000000001",
            json={"name": "X"},
            headers=_auth(admin),
        )
        consultado = await client.get(
            f"{URL}/00000000-0000-0000-0000-000000000001", headers=_auth(admin)
        )

    assert response.status_code == 404
    assert _code(response) == "client_not_found"
    assert consultado.status_code == 404


# Criterio 4: contactos con al menos un dato; uno o más reciben el informe mensual.
async def test_agregar_contactos_y_marcar_informe(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Sanatorio Ficticio")
        contactos_url = f"{URL}/{creado['id']}/contacts"
        uno = await client.post(
            contactos_url,
            json={"name": "Ana Pérez", "email": "ana@ejemplo.com", "receives_monthly_report": True},
            headers=_auth(admin),
        )
        dos = await client.post(contactos_url, json={"phone": "3855000000"}, headers=_auth(admin))
        listado = await client.get(contactos_url, headers=_auth(admin))

    assert uno.status_code == 201, uno.text
    assert dos.status_code == 201, dos.text
    assert uno.json()["receives_monthly_report"] is True
    assert dos.json()["receives_monthly_report"] is False
    assert dos.json()["name"] is None
    assert sorted(c["phone"] or "" for c in listado.json()) == ["", "3855000000"]


async def test_editar_contacto(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Cliente")
        contactos_url = f"{URL}/{creado['id']}/contacts"
        contacto = await client.post(contactos_url, json={"name": "Ana"}, headers=_auth(admin))
        editado = await client.patch(
            f"{contactos_url}/{contacto.json()['id']}",
            json={"email": "ana@ejemplo.com", "receives_monthly_report": True},
            headers=_auth(admin),
        )

    assert editado.status_code == 200, editado.text
    assert editado.json()["name"] == "Ana"
    assert editado.json()["receives_monthly_report"] is True


async def test_contacto_sin_ningun_dato_se_rechaza(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Cliente")
        contactos_url = f"{URL}/{creado['id']}/contacts"
        vacio = await client.post(
            contactos_url, json={"name": "   ", "phone": ""}, headers=_auth(admin)
        )
        contacto = await client.post(contactos_url, json={"phone": "123"}, headers=_auth(admin))
        vaciado = await client.patch(
            f"{contactos_url}/{contacto.json()['id']}", json={"phone": None}, headers=_auth(admin)
        )

    assert vacio.status_code == 422
    assert _code(vacio) == "contact_without_data"
    assert vaciado.status_code == 422
    assert _code(vaciado) == "contact_without_data"


async def test_contacto_de_cliente_o_contacto_inexistente_da_404(admin: User) -> None:
    async with _client() as client:
        sin_cliente = await client.post(
            f"{URL}/00000000-0000-0000-0000-000000000001/contacts",
            json={"name": "Ana"},
            headers=_auth(admin),
        )
        creado = await _crear(client, admin, name="Cliente")
        sin_contacto = await client.patch(
            f"{URL}/{creado['id']}/contacts/00000000-0000-0000-0000-000000000001",
            json={"name": "Ana"},
            headers=_auth(admin),
        )

    assert sin_cliente.status_code == 404
    assert _code(sin_cliente) == "client_not_found"
    assert sin_contacto.status_code == 404
    assert _code(sin_contacto) == "contact_not_found"


async def test_contacto_de_otro_cliente_da_404(admin: User) -> None:
    async with _client() as client:
        uno = await _crear(client, admin, name="Cliente Uno")
        otro = await _crear(client, admin, name="Cliente Otro")
        contacto = await client.post(
            f"{URL}/{uno['id']}/contacts", json={"name": "Ana"}, headers=_auth(admin)
        )
        response = await client.patch(
            f"{URL}/{otro['id']}/contacts/{contacto.json()['id']}",
            json={"name": "Beto"},
            headers=_auth(admin),
        )

    assert response.status_code == 404


# Criterio 5: el contacto que recibe el informe mensual tiene que tener email.
async def test_informe_mensual_sin_email_se_rechaza(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Cliente")
        contactos_url = f"{URL}/{creado['id']}/contacts"
        sin_email = await client.post(
            contactos_url,
            json={"name": "Ana", "receives_monthly_report": True},
            headers=_auth(admin),
        )
        contacto = await client.post(
            contactos_url,
            json={"name": "Beto", "email": "beto@ejemplo.com", "receives_monthly_report": True},
            headers=_auth(admin),
        )
        sacar_email = await client.patch(
            f"{contactos_url}/{contacto.json()['id']}", json={"email": None}, headers=_auth(admin)
        )

    assert sin_email.status_code == 422
    assert _code(sin_email) == "monthly_report_requires_email"
    assert "email" in sin_email.json()["detail"]["message"]
    assert sacar_email.status_code == 422
    assert _code(sacar_email) == "monthly_report_requires_email"


# Criterio 6: un email con formato inválido se rechaza.
async def test_email_invalido_se_rechaza(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Cliente")
        response = await client.post(
            f"{URL}/{creado['id']}/contacts", json={"email": "no-es-un-mail"}, headers=_auth(admin)
        )

    assert response.status_code == 422


# Criterio 7: un nombre muy parecido a otro se advierte, pero no se rechaza.
async def test_nombres_parecidos_se_advierten(admin: User) -> None:
    async with _client() as client:
        existente = await _crear(client, admin, name="Farmacia Del Sol")
        await _crear(client, admin, name="Ferretería Central")
        igual = await client.get(
            f"{URL}/similar", params={"name": "  farmacia   del SOL "}, headers=_auth(admin)
        )
        acentos = await client.get(
            f"{URL}/similar", params={"name": "Fármacia del Sol"}, headers=_auth(admin)
        )
        contiene = await client.get(
            f"{URL}/similar", params={"name": "Farmacia del Sol Termas"}, headers=_auth(admin)
        )
        distinto = await client.get(
            f"{URL}/similar", params={"name": "Panadería Norte"}, headers=_auth(admin)
        )
        duplicado = await client.post(URL, json={"name": "Farmacia Del Sol"}, headers=_auth(admin))

    for response in (igual, acentos, contiene):
        assert response.status_code == 200, response.text
        assert [c["id"] for c in response.json()] == [existente["id"]]
    assert distinto.json() == []
    assert duplicado.status_code == 201


async def test_parecidos_excluye_al_mismo_cliente_y_a_nombres_cortos(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, name="Farmacia Del Sol")
        mismo = await client.get(
            f"{URL}/similar",
            params={"name": "Farmacia Del Sol", "exclude_id": creado["id"]},
            headers=_auth(admin),
        )
        corto = await client.get(f"{URL}/similar", params={"name": "Sol"}, headers=_auth(admin))

    assert mismo.json() == []
    # Un nombre muy corto no se compara por contención: "Sol" no avisa por "Farmacia Del Sol".
    assert corto.json() == []


# Criterio 8: un número que ya existe se rechaza.
async def test_numero_duplicado_se_rechaza(admin: User) -> None:
    await _seed([Client(number="10642", name="Migrado")])
    async with SessionLocal() as session:
        with pytest.raises(clients_service.ClientNumberAlreadyExistsError):
            await clients_service.create_client(session, ClientCreate(name="Otro"), number="10642")


# Criterio 9: nombre vacío o de solo espacios se rechaza.
async def test_nombre_vacio_se_rechaza(admin: User) -> None:
    async with _client() as client:
        vacio = await client.post(URL, json={"name": "   "}, headers=_auth(admin))
        creado = await _crear(client, admin, name="Cliente")
        renombrar = await client.patch(
            f"{URL}/{creado['id']}", json={"name": ""}, headers=_auth(admin)
        )
        nulo = await client.patch(
            f"{URL}/{creado['id']}", json={"name": None}, headers=_auth(admin)
        )

    assert vacio.status_code == 422
    assert renombrar.status_code == 422
    assert nulo.status_code == 422


# Criterio 10: listado con número, nombre y segmento, paginado y filtrable por segmento.
async def test_listado_paginado_y_ordenado_por_nombre(admin: User) -> None:
    await _seed([Client(number=str(n), name=f"Cliente {n:02d}") for n in range(1, 6)])
    async with _client() as client:
        pagina = await client.get(URL, params={"limit": 2, "offset": 2}, headers=_auth(admin))

    body = pagina.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 2
    assert [(c["number"], c["name"]) for c in body["items"]] == [
        ("3", "Cliente 03"),
        ("4", "Cliente 04"),
    ]
    assert body["items"][0]["segment"] == "unclassified"


async def test_listado_filtra_por_segmento_y_excluye_dados_de_baja(admin: User) -> None:
    from datetime import UTC, datetime

    from app.db.models.client import ClientSegment

    await _seed(
        [
            Client(number="1", name="Hotel A", segment=ClientSegment.hotel),
            Client(number="2", name="Comercio B", segment=ClientSegment.business),
            Client(
                number="3",
                name="Hotel Viejo",
                segment=ClientSegment.hotel,
                deleted_at=datetime.now(UTC),
            ),
        ]
    )
    async with _client() as client:
        hoteles = await client.get(URL, params={"segment": "hotel"}, headers=_auth(admin))
        todos = await client.get(URL, headers=_auth(admin))

    assert [c["name"] for c in hoteles.json()["items"]] == ["Hotel A"]
    assert hoteles.json()["total"] == 1
    assert todos.json()["total"] == 2


async def test_listado_rechaza_limite_fuera_de_rango(admin: User) -> None:
    async with _client() as client:
        response = await client.get(URL, params={"limit": 0}, headers=_auth(admin))
        grande = await client.get(URL, params={"limit": 1000}, headers=_auth(admin))

    assert response.status_code == 422
    assert grande.status_code == 422


# Criterio 11: técnico y dirección reciben acceso denegado.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(schema: None, role: UserRole) -> None:
    usuario = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([usuario])
    cliente = Client(number="1", name="Cliente")
    await _seed([cliente])
    base = f"{URL}/{cliente.id}"
    async with _client() as client:
        respuestas = [
            await client.get(URL, headers=_auth(usuario)),
            await client.post(URL, json={"name": "X"}, headers=_auth(usuario)),
            await client.get(f"{URL}/similar", params={"name": "X"}, headers=_auth(usuario)),
            await client.get(base, headers=_auth(usuario)),
            await client.patch(base, json={"name": "X"}, headers=_auth(usuario)),
            await client.get(f"{base}/contacts", headers=_auth(usuario)),
            await client.post(f"{base}/contacts", json={"name": "X"}, headers=_auth(usuario)),
        ]

    assert [r.status_code for r in respuestas] == [403] * len(respuestas)
