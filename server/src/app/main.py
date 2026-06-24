from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from pathlib import Path

from src.app.features.dashboard.kpi_service import refresh_kpis_background

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.app.security.rate_limit import limiter

from src.app.features.catalogs.service import ensure_default_catalogs
from src.app.features.dashboard.routes import api_router as dashboard_api_router
from src.app.features.etl_status.routes import JSON_API as etl_status_json_router
from src.app.features.ta02_crud.routes import router as crud_router
from src.app.modules.account.routes import api_router as account_api_router
from src.app.modules.audit.routes import router as audit_router
from src.app.modules.admin.routes import api_router as admin_api_router
from src.app.modules.admin.service import ensure_user_status_field
from src.app.modules.auth.collections import ensure_auth_collections
from src.app.modules.auth.routes import api_router as auth_api_router
from src.app.modules.auth.routes import router as auth_module_router
from src.app.modules.auth.routes import web_router as auth_web_router
from src.app.modules.hotels.routes import api_router as hotels_api_router
from src.app.modules.hotels.routes import router as hotels_module_router
from src.app.modules.partner.routes import api_router as partner_api_router
from src.app.modules.partner.routes import legacy_admin_api_router as partner_legacy_admin_api_router
from src.app.modules.partner.routes import router as partner_module_router
from src.app.modules.settings.routes import api_router as settings_api_router
from src.app.modules.reservations.routes import api_router as reservations_api_router
from src.app.modules.reservations.routes import management_api_router as reservations_management_api_router
from src.app.modules.reservations.routes import router as reservations_module_router
from src.app.modules.revenue.routes import api_router as revenue_api_router
from src.app.modules.revenue.routes import router as revenue_module_router
from src.app.modules.reviews.routes import api_router as reviews_api_router
from src.app.modules.reviews.routes import router as reviews_module_router
from src.app.modules.billing.routes import api_router as billing_api_router
from src.app.modules.billing.routes import router as billing_module_router
from src.app.modules.users.routes import router as users_module_router
from src.app.routes.system import router as system_router
from src.app.security.middleware import role_access_middleware
from src.app.security.session import ensure_user_sessions_indexes, ensure_users_indexes
from src.app.modules.partner.services.bootstrap import (
    ensure_hotel_content_collections,
    ensure_hotel_profile_collections,
    ensure_inventory_collections,
    ensure_rate_collections,
)
from src.app.modules.revenue.services import ensure_revenue_collections
from src.app.modules.reviews.service import ensure_reviews_collections
from src.app.modules.billing.service import ensure_billing_collections
from src.app.modules.reservations.service import ensure_reservation_collections
from config.settings import get_settings
from src.database.connection import get_database


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HotelData Hub", version="1.0.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=list(settings.cors_allowed_methods),
        allow_headers=list(settings.cors_allowed_headers),
    )
    app.middleware("http")(role_access_middleware)
    app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")
    uploads_dir = settings.project_root / "data" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
    app.include_router(dashboard_api_router)
    app.include_router(etl_status_json_router)
    app.include_router(audit_router)
    app.include_router(admin_api_router)
    app.include_router(auth_module_router)
    app.include_router(auth_api_router)
    app.include_router(auth_web_router)
    app.include_router(users_module_router)
    app.include_router(hotels_api_router)
    app.include_router(hotels_module_router)
    app.include_router(partner_api_router)
    app.include_router(partner_legacy_admin_api_router)
    app.include_router(revenue_api_router)
    app.include_router(reviews_api_router)
    app.include_router(reviews_module_router)
    app.include_router(billing_api_router)
    app.include_router(billing_module_router)
    app.include_router(reservations_api_router)
    app.include_router(reservations_management_api_router)
    app.include_router(reservations_module_router)
    app.include_router(partner_module_router)
    app.include_router(revenue_module_router)
    app.include_router(settings_api_router)
    app.include_router(account_api_router)
    app.include_router(system_router)
    app.include_router(crud_router)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_default_catalogs()
    ensure_user_status_field()
    ensure_user_sessions_indexes(get_database())
    ensure_users_indexes(get_database())
    ensure_hotel_content_collections()
    ensure_hotel_profile_collections()
    ensure_inventory_collections()
    ensure_rate_collections()
    ensure_revenue_collections()
    ensure_reviews_collections()
    ensure_billing_collections()
    ensure_reservation_collections()
    ensure_auth_collections()
    threading.Thread(target=refresh_kpis_background, daemon=True).start()
    yield


app = create_app()
