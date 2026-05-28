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
    @app.on_event("startup")
    def _seed_default_catalogs() -> None:
        ensure_default_catalogs()
    return app


app = create_app()
