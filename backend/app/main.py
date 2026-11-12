from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    audit,
    auth,
    catalog_csv,
    clients,
    crews,
    documents,
    equipment,
    equipment_types,
    failures,
    files,
    health,
    invoices,
    maintenance,
    order_materials,
    other_texts,
    parts,
    repairs,
    search,
    stock,
    tech_orders,
    users,
    work_orders,
    work_types,
)
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db import audit_listener  # noqa: F401  (registra la auditoría de cambios)


def create_app() -> FastAPI:
    settings = get_settings()
    settings.require_storage()
    app = FastAPI(title="OT Platform API", version="0.1.0")
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(audit.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(work_types.router)
    app.include_router(equipment_types.router)
    app.include_router(failures.router)
    app.include_router(repairs.router)
    app.include_router(parts.router)
    app.include_router(clients.router)
    app.include_router(clients.sites_router)
    app.include_router(equipment.router)
    app.include_router(work_orders.router)
    app.include_router(order_materials.router)
    app.include_router(documents.router)
    app.include_router(other_texts.router)
    app.include_router(catalog_csv.router)
    app.include_router(invoices.router)
    app.include_router(crews.router)
    app.include_router(crews.technicians_router)
    app.include_router(tech_orders.router)
    app.include_router(files.router)
    app.include_router(search.router)
    app.include_router(stock.router)
    app.include_router(stock.tech_router)
    app.include_router(maintenance.router)
    return app


app = create_app()
