from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from app.core.security import create_access_token
from app.db.models.part import Part, PartPrice
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

# E02-05 y E02-06: administración mantiene los materiales y su precio de lista.

TABLES = [User.__table__, Part.__table__, PartPrice.__table__]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([user])
    return user


async def _seed(users: Sequence[User]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(users))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _crear(client: AsyncClient, admin: User, name: str, unit: str = "kg") -> dict[str, str]:
    response = await client.post(
        "/admin/parts", json={"name": name, "unit": unit}, headers=_auth(admin)
    )
    assert response.status_code == 201, response.text
    body: dict[str, str] = response.json()
    return body


# Todo material arranca con precio 0, que después completa administración.
async def test_material_nuevo_arranca_en_cero(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, "  Gas   R410A ")

    assert creado["name"] == "Gas R410A"
    assert creado["unit"] == "kg"
    assert creado["list_price"] == "0.00"
    assert creado["is_active"] is True


# E02-06, criterio 1: cambiar el precio agrega uno nuevo y conserva los anteriores.
async def test_cambiar_precio_conserva_el_historial(admin: User) -> None:
    async with _client() as client:
        gas = await _crear(client, admin, "Gas R410A")
        primero = await client.put(
            f"/admin/parts/{gas['id']}/price", json={"list_price": "1500.50"}, headers=_auth(admin)
        )
        segundo = await client.put(
            f"/admin/parts/{gas['id']}/price", json={"list_price": "1800"}, headers=_auth(admin)
        )
        listado = await client.get("/admin/parts", headers=_auth(admin))

    assert primero.status_code == 200, primero.text
    assert primero.json()["list_price"] == "1500.50"
    assert segundo.json()["list_price"] == "1800.00"
    assert listado.json()[0]["list_price"] == "1800.00"
    async with SessionLocal() as session:
        precios = (await session.scalars(select(PartPrice))).all()
    assert len(precios) == 3
    assert {p.created_by for p in precios} == {admin.id}


# E02-05: no puede haber dos materiales con el mismo nombre (sin distinguir mayúsculas).
async def test_nombre_repetido_da_conflicto(admin: User) -> None:
    async with _client() as client:
        await _crear(client, admin, "Gas R410A")
        repetido = await client.post(
            "/admin/parts", json={"name": "gas r410a", "unit": "kg"}, headers=_auth(admin)
        )

    assert repetido.status_code == 409
    assert repetido.json()["detail"]["code"] == "part_name_already_exists"


# E02-05, criterio 4: un material no se borra, se desactiva.
async def test_desactivado_no_sale_en_el_listado_por_defecto(admin: User) -> None:
    async with _client() as client:
        gas = await _crear(client, admin, "Gas R410A")
        await _crear(client, admin, "Capacitor 35 uF", "unidad")
        desactivado = await client.patch(
            f"/admin/parts/{gas['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        activos = await client.get("/admin/parts", headers=_auth(admin))
        todos = await client.get(
            "/admin/parts", params={"include_inactive": True}, headers=_auth(admin)
        )

    assert desactivado.status_code == 200
    assert desactivado.json()["is_active"] is False
    assert [p["name"] for p in activos.json()] == ["Capacitor 35 uF"]
    assert [p["name"] for p in todos.json()] == ["Capacitor 35 uF", "Gas R410A"]
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(Part)) == 2


async def test_renombrar_y_cambiar_unidad(admin: User) -> None:
    async with _client() as client:
        cano = await _crear(client, admin, "Caño 1/4", "unidad")
        editado = await client.patch(
            f"/admin/parts/{cano['id']}",
            json={"name": "Caño de cobre 1/4", "unit": "metro"},
            headers=_auth(admin),
        )

    assert editado.status_code == 200
    assert editado.json()["name"] == "Caño de cobre 1/4"
    assert editado.json()["unit"] == "metro"


@pytest.mark.parametrize("precio", ["-1", "1.234", "abc"])
async def test_precio_invalido_se_rechaza(admin: User, precio: str) -> None:
    async with _client() as client:
        gas = await _crear(client, admin, "Gas R410A")
        response = await client.put(
            f"/admin/parts/{gas['id']}/price", json={"list_price": precio}, headers=_auth(admin)
        )

    assert response.status_code == 422


async def test_material_inexistente_da_404(admin: User) -> None:
    falta = "00000000-0000-0000-0000-000000000001"
    async with _client() as client:
        precio = await client.put(
            f"/admin/parts/{falta}/price", json={"list_price": "1"}, headers=_auth(admin)
        )
        edicion = await client.patch(
            f"/admin/parts/{falta}", json={"is_active": False}, headers=_auth(admin)
        )

    assert precio.status_code == 404
    assert precio.json()["detail"]["code"] == "part_not_found"
    assert edicion.status_code == 404


# Regla 1 y 8: solo administración; el técnico y dirección reciben 403.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_otros_roles_no_acceden(admin: User, role: UserRole) -> None:
    otro = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([otro])
    async with _client() as client:
        gas = await _crear(client, admin, "Gas R410A")
        respuestas = [
            await client.get("/admin/parts", headers=_auth(otro)),
            await client.post(
                "/admin/parts", json={"name": "Otro", "unit": "kg"}, headers=_auth(otro)
            ),
            await client.patch(
                f"/admin/parts/{gas['id']}", json={"is_active": False}, headers=_auth(otro)
            ),
            await client.put(
                f"/admin/parts/{gas['id']}/price", json={"list_price": "1"}, headers=_auth(otro)
            ),
        ]

    assert [r.status_code for r in respuestas] == [403, 403, 403, 403]
