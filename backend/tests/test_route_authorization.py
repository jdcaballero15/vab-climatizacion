import uuid
from collections.abc import AsyncGenerator, Sequence
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api.deps import require_role
from app.core.security import create_access_token
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

# Rutas públicas que no exigen rol (salud, login y la documentación autogenerada).
PUBLIC_PATHS = {
    "/health",
    "/health/ready",
    "/auth/login",
    # El refresco y el cierre se autentican con el token de refresco en el cuerpo, no con rol.
    "/auth/refresh",
    "/auth/logout",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=[User.__table__])
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=[User.__table__])
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


async def _seed(users: Sequence[User]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(users))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client(target: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=target), base_url="http://test")


def _guarded_app() -> FastAPI:
    """App de prueba con rutas de admin y de técnico que usan el require_role real."""
    test_app = FastAPI()

    @test_app.get("/admin/tablero")
    async def admin_only(
        _: Annotated[User, Depends(require_role(UserRole.admin))],
    ) -> dict[str, bool]:
        return {"ok": True}

    @test_app.get("/tech/mis-ordenes")
    async def tech_only(
        _: Annotated[User, Depends(require_role(UserRole.technician))],
    ) -> dict[str, bool]:
        return {"ok": True}

    @test_app.get("/tech/recurso/{owner_id}")
    async def recurso(
        owner_id: str,
        user: Annotated[User, Depends(require_role(UserRole.technician))],
    ) -> dict[str, bool]:
        # Patrón del criterio 2: un recurso que no es del técnico responde 404, no 403.
        if owner_id != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "not_found", "message": "No encontrado."},
            )
        return {"ok": True}

    return test_app


# ---- Criterio 5: ninguna ruta no pública queda sin rol declarado ----


def _api_routes(routes: object) -> list[APIRoute]:
    """Junta las APIRoute, recorriendo los routers incluidos (FastAPI 0.143+)."""
    collected: list[APIRoute] = []
    for route in routes:  # type: ignore[attr-defined]
        if isinstance(route, APIRoute):
            collected.append(route)
        elif hasattr(route, "original_router"):
            collected.extend(_api_routes(route.original_router.routes))
        elif hasattr(route, "routes"):
            collected.extend(_api_routes(route.routes))
    return collected


def _dependency_calls(dependant: object) -> list[object]:
    calls: list[object] = []
    for dep in dependant.dependencies:  # type: ignore[attr-defined]
        if dep.call is not None:
            calls.append(dep.call)
        calls.extend(_dependency_calls(dep))
    return calls


def _has_role_guard(route: APIRoute) -> bool:
    return any(
        getattr(call, "required_roles", None) is not None
        for call in _dependency_calls(route.dependant)
    )


def test_toda_ruta_no_publica_declara_rol() -> None:
    offenders = [
        f"{sorted(route.methods)} {route.path}"
        for route in _api_routes(app.routes)
        if route.path not in PUBLIC_PATHS and not _has_role_guard(route)
    ]
    assert offenders == [], f"Rutas sin rol declarado: {offenders}"


# ---- Criterio 1 y 4: /auth/me (cualquier rol autenticado), permitido y denegado ----


async def test_me_con_token_devuelve_el_usuario(schema: None) -> None:
    user = make_user(email="ana@ot-demo.com", role=UserRole.admin)
    await _seed([user])
    async with _client(app) as client:
        response = await client.get("/auth/me", headers=_auth(user))
    assert response.status_code == 200
    assert response.json()["email"] == "ana@ot-demo.com"


async def test_me_sin_token_devuelve_401(schema: None) -> None:
    async with _client(app) as client:
        response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_token_invalido_devuelve_401(schema: None) -> None:
    async with _client(app) as client:
        response = await client.get("/auth/me", headers={"Authorization": "Bearer basura"})
    assert response.status_code == 401


async def test_me_usuario_inactivo_devuelve_401(schema: None) -> None:
    user = make_user(email="baja@ot-demo.com", is_active=False)
    await _seed([user])
    async with _client(app) as client:
        response = await client.get("/auth/me", headers=_auth(user))
    assert response.status_code == 401


# ---- Criterio 3 y 4: rol correcto entra, rol incorrecto recibe 403 ----


async def test_admin_entra_ruta_admin_y_tecnico_recibe_403(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tech = make_user(email="tec@ot-demo.com", role=UserRole.technician)
    await _seed([admin, tech])
    async with _client(_guarded_app()) as client:
        permitido = await client.get("/admin/tablero", headers=_auth(admin))
        denegado = await client.get("/admin/tablero", headers=_auth(tech))
    assert permitido.status_code == 200
    assert denegado.status_code == 403


async def test_tecnico_entra_ruta_tecnico_y_admin_recibe_403(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tech = make_user(email="tec@ot-demo.com", role=UserRole.technician)
    await _seed([admin, tech])
    async with _client(_guarded_app()) as client:
        permitido = await client.get("/tech/mis-ordenes", headers=_auth(tech))
        denegado = await client.get("/tech/mis-ordenes", headers=_auth(admin))
    assert permitido.status_code == 200
    assert denegado.status_code == 403


# ---- Criterio 2: un recurso que no es del técnico responde 404, no 403 ----


async def test_tecnico_recurso_ajeno_devuelve_404(schema: None) -> None:
    tech = make_user(email="tec@ot-demo.com", role=UserRole.technician)
    await _seed([tech])
    async with _client(_guarded_app()) as client:
        response = await client.get(f"/tech/recurso/{uuid.uuid4()}", headers=_auth(tech))
    assert response.status_code == 404
