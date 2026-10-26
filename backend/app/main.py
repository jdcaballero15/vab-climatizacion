from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    clients,
    equipment,
    equipment_types,
    failures,
    health,
    repairs,
    users,
    work_types,
)
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="OT Platform API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(work_types.router)
    app.include_router(equipment_types.router)
    app.include_router(failures.router)
    app.include_router(repairs.router)
    app.include_router(clients.router)
    app.include_router(clients.sites_router)
    app.include_router(equipment.router)
    return app


app = create_app()
