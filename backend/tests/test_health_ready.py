from httpx import ASGITransport, AsyncClient

from app.main import app

# Criterio 1: con el entorno levantado, GET /health/ready confirma que la base responde.


async def test_health_ready_reports_database_ok() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
