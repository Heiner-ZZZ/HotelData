from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.app.features.audit.routes import router as audit_router
from src.app.features.catalogs.routes import router as catalogs_router
from src.app.features.catalogs.service import ensure_default_catalogs
from src.app.features.collections.routes import router as collections_router
from src.app.features.company.routes import router as company_router
from src.app.features.dashboard.routes import router as dashboard_router
from src.app.features.etl_status.routes import router as etl_status_router
from src.app.features.problems.routes import router as problems_router
from src.app.features.quality.routes import router as quality_router
from src.app.features.records.routes import router as records_router
from src.app.features.ta02_crud.routes import router as crud_router
from src.app.features.ta02_crud.routes import web_router as ta02_web_router
from src.app.modules.audit.routes import router as modular_audit_router
from src.app.modules.admin.routes import router as admin_router
from src.app.modules.auth.routes import router as auth_module_router
from src.app.modules.auth.routes import web_router as auth_web_router
from src.app.modules.hotels.routes import router as hotels_module_router
from src.app.modules.partner.routes import router as partner_module_router
from src.app.modules.reservations.routes import router as reservations_module_router
from src.app.modules.revenue.routes import router as revenue_module_router
from src.app.modules.users.routes import router as users_module_router
from src.app.routes.system import router as system_router


def create_app() -> FastAPI:
    app = FastAPI(title="HotelData Hub", version="1.0.0")
    app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")
    app.include_router(dashboard_router)
    app.include_router(records_router)
    app.include_router(etl_status_router)
    app.include_router(quality_router)
    app.include_router(collections_router)
    app.include_router(company_router)
    app.include_router(problems_router)
    app.include_router(catalogs_router, prefix="/catalogs")
    app.include_router(audit_router)
    app.include_router(ta02_web_router)
    app.include_router(crud_router)
    app.include_router(auth_web_router)
    app.include_router(admin_router)
    app.include_router(auth_module_router)
    app.include_router(users_module_router)
    app.include_router(hotels_module_router)
    app.include_router(reservations_module_router)
    app.include_router(partner_module_router)
    app.include_router(revenue_module_router)
    app.include_router(modular_audit_router)
    app.include_router(system_router)
    @app.on_event("startup")
    def _seed_default_catalogs() -> None:
        ensure_default_catalogs()
    return app


app = create_app()
