from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from pathlib import Path

# ── Global ObjectId → str serialization — patched BEFORE FastAPI routing ──
import fastapi.encoders as _encoders_module
import fastapi.routing as _routing_module
from bson import ObjectId
from pydantic import BaseModel

_original_je = _encoders_module.jsonable_encoder

def _patched_jsonable_encoder(obj, **kwargs):
    """Patched jsonable_encoder that converts ObjectId to str recursively.

    Also handles Pydantic BaseModel instances whose dict/list fields contain
    ObjectId values. Pydantic v2's model_dump(mode="json") bypasses custom
    encoders for untyped nested data, so we pre-convert models to plain
    dictionaries using model_dump()/dict() and then walk the result.
    """
    def _walk(o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, dict):
            return {k: _walk(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return type(o)(_walk(v) for v in o)
        if isinstance(o, BaseModel):
            valid_keys = {"include", "exclude", "by_alias", "exclude_unset", "exclude_defaults", "exclude_none"}
            dump_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
            dump_method = getattr(o, "model_dump", getattr(o, "dict", None))
            d = dump_method(**dump_kwargs) if dump_method else o
            return _walk(d)
        return o

    custom_encoder = kwargs.pop("custom_encoder", {}) or {}
    custom_encoder[ObjectId] = str
    kwargs["custom_encoder"] = custom_encoder

    return _original_je(_walk(obj), **kwargs)

_encoders_module.jsonable_encoder = _patched_jsonable_encoder
_routing_module.jsonable_encoder = _patched_jsonable_encoder
# ──────────────────────────────────────────────────────────

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import get_settings
from src.app.ai.routes import api_router as ai_api_router
from src.app.core.outbox import (
    ensure_outbox_collection,
    process_pending_outbox,
    process_pending_outbox_forever,
)
from src.app.features.catalogs.service import ensure_default_catalogs
from src.app.features.dashboard.kpi_service import refresh_kpis_background
from src.app.features.dashboard.routes import api_router as dashboard_api_router
from src.app.features.etl_status.routes import JSON_API as etl_status_json_router
from src.app.features.etl_status_m2c.routes import (
    JSON_API as etl_status_m2c_json_router,
)
from src.app.features.ta02_crud.routes import router as crud_router
from src.app.modules.account.routes import api_router as account_api_router
from src.app.modules.admin.routes import api_router as admin_api_router
from src.app.modules.admin.service import ensure_user_status_field
from src.app.modules.amenities.routes import admin_router as amenities_admin_router
from src.app.modules.amenities.routes import guest_router as amenities_guest_router
from src.app.modules.amenities.routes import photos_router as amenities_photos_router
from src.app.modules.analytics.routes import router as analytics_router
from src.app.modules.audit.routes import router as audit_router
from src.app.modules.auth.collections import ensure_auth_collections
from src.app.modules.auth.routes import api_router as auth_api_router
from src.app.modules.auth.routes import router as auth_module_router
from src.app.modules.auth.routes import web_router as auth_web_router
from src.app.modules.billing.routes import api_router as billing_api_router
from src.app.modules.billing.routes import router as billing_module_router
from src.app.modules.billing.service import ensure_billing_collections
from src.app.modules.expenses.routes import api_router as expenses_api_router
from src.app.modules.expenses.routes import router as expenses_module_router
from src.app.modules.expenses.service.collections import ensure_expenses_collections
from src.app.modules.expenses.vendor_ap_routes import api_router as vendor_ap_api_router
from src.app.modules.financial_reconciliation.domain_events import (
    ensure_domain_event_collections,
)
from src.app.modules.financial_reconciliation.routes import (
    api_router as financial_reconciliation_api_router,
)
from src.app.modules.geo_catalog.routes import api_router as geo_catalog_api_router
from src.app.modules.geo_catalog.service import ensure_geo_collections
from src.app.modules.global_settings.routes import (
    api_router as global_settings_api_router,
)
from src.app.modules.global_settings.service import ensure_global_settings_collections
from src.app.modules.hotel_permissions.routes import (
    api_router as hotel_permissions_api_router,
)
from src.app.modules.hotels.collections import ensure_hotels_collections
from src.app.modules.hotels.routes import api_router as hotels_api_router
from src.app.modules.hotels.routes import router as hotels_module_router
from src.app.modules.housekeeping.routes import api_router as housekeeping_api_router
from src.app.modules.housekeeping.routes import router as housekeeping_module_router
from src.app.modules.housekeeping.service import ensure_housekeeping_collections
from src.app.modules.hr.routes import api_router as hr_api_router
from src.app.modules.hr.routes import router as hr_module_router
from src.app.modules.hr.service.collections import ensure_hr_collections
from src.app.modules.instay.routes import guest_router as instay_guest_router
from src.app.modules.instay.routes import staff_router as instay_staff_router
from src.app.modules.kpi.routes import router as kpi_api_router
from src.app.modules.legal.routes import admin_router as legal_admin_router
from src.app.modules.legal.routes import public_router as legal_public_router
from src.app.modules.legal.service import ensure_legal_collections
from src.app.modules.lost_and_found.routes import (
    api_router as lost_and_found_api_router,
)
from src.app.modules.lost_and_found.routes import router as lost_and_found_module_router
from src.app.modules.lost_and_found.service import ensure_lost_and_found_collections
from src.app.modules.map.routes import router as map_api_router
from src.app.modules.notifications.promotions import (
    ensure_promotions_collection,
    ensure_scheduled_promotions_collection,
    process_due_scheduled_promotions_forever,
)
from src.app.modules.notifications.routes import router as notifications_router
from src.app.modules.partner.routes import api_router as partner_api_router
from src.app.modules.partner.routes import (
    legacy_admin_api_router as partner_legacy_admin_api_router,
)
from src.app.modules.partner.routes import public_router as partner_public_router
from src.app.modules.partner.routes import router as partner_module_router
from src.app.modules.partner.routes.hotel_products import router as products_api_router
from src.app.modules.partner.services.audit import ensure_audit_indexes
from src.app.modules.partner.services.bootstrap import (
    ensure_hotel_content_collections,
    ensure_hotel_profile_collections,
    ensure_inventory_collections,
    ensure_rate_collections,
    ensure_room_features_collections,
)
from src.app.modules.property_approval.routes import (
    api_router as property_approval_api_router,
)
from src.app.modules.reception import ensure_reception_collections
from src.app.modules.reception.routes import api_router as reception_api_router
from src.app.modules.reports.routes import router as reports_router
from src.app.modules.reservations.routes import api_router as reservations_api_router
from src.app.modules.reservations.routes import (
    management_api_router as reservations_management_api_router,
)
from src.app.modules.reservations.routes import router as reservations_module_router
from src.app.modules.reservations.routes.reception_calendar import (
    reception_calendar_router,
)
from src.app.modules.reservations.routes.self_checkin import (
    public_router as self_checkin_public_router,
)
from src.app.modules.reservations.service import ensure_reservation_collections
from src.app.modules.revenue.routes import api_router as revenue_api_router
from src.app.modules.revenue.routes import router as revenue_module_router
from src.app.modules.revenue.services import ensure_revenue_collections
from src.app.modules.reviews.routes import api_router as reviews_api_router
from src.app.modules.reviews.routes import public_router as reviews_public_router
from src.app.modules.reviews.routes import router as reviews_module_router
from src.app.modules.reviews.service import ensure_reviews_collections
from src.app.modules.settings.routes import api_router as settings_api_router
from src.app.modules.strategic.routes import router as strategic_router
from src.app.modules.subscriptions import ensure_subscription_collections
from src.app.modules.subscriptions.routes import api_router as subscriptions_api_router
from src.app.modules.subscriptions.routes_admin import api_router as subscriptions_admin_api_router
from src.app.modules.tracking.routes import tracking_api_router
from src.app.modules.users.routes import router as users_module_router
from src.app.routes.system import router as system_router
from src.app.security.collections import ensure_hotel_permission_collections
from src.app.security.middleware import role_access_middleware
from src.app.security.rate_limit import limiter
from src.app.security.session import ensure_user_sessions_indexes, ensure_users_indexes
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="HotelData", version="1.0.0", lifespan=lifespan)
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
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    uploads_dir = settings.project_root / "data" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
    app.include_router(dashboard_api_router)
    app.include_router(ai_api_router)
    app.include_router(etl_status_json_router)
    app.include_router(etl_status_m2c_json_router)
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
    app.include_router(partner_public_router)
    app.include_router(revenue_api_router)
    app.include_router(reviews_api_router)
    app.include_router(reviews_public_router)
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
    app.include_router(analytics_router)
    app.include_router(strategic_router)
    app.include_router(housekeeping_api_router)
    app.include_router(housekeeping_module_router)
    app.include_router(tracking_api_router)
    app.include_router(products_api_router)
    app.include_router(global_settings_api_router)
    app.include_router(geo_catalog_api_router)
    app.include_router(kpi_api_router)
    app.include_router(reception_calendar_router)
    app.include_router(self_checkin_public_router)
    app.include_router(legal_public_router)
    app.include_router(legal_admin_router)
    app.include_router(map_api_router)
    app.include_router(amenities_guest_router)
    app.include_router(amenities_admin_router)
    app.include_router(amenities_photos_router)
    app.include_router(reception_api_router)
    app.include_router(lost_and_found_api_router)
    app.include_router(lost_and_found_module_router)
    app.include_router(notifications_router)
    app.include_router(hr_api_router)
    app.include_router(hr_module_router)
    app.include_router(expenses_api_router)
    app.include_router(expenses_module_router)
    app.include_router(vendor_ap_api_router)
    app.include_router(financial_reconciliation_api_router)
    app.include_router(instay_guest_router)
    app.include_router(instay_staff_router)
    app.include_router(crud_router)
    app.include_router(reports_router)
    app.include_router(hotel_permissions_api_router)
    app.include_router(property_approval_api_router)
    app.include_router(subscriptions_api_router)
    app.include_router(subscriptions_admin_api_router)
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
    ensure_subscription_collections()
    ensure_domain_event_collections()
    ensure_housekeeping_collections()
    ensure_reservation_collections()
    ensure_reception_collections()
    ensure_global_settings_collections()
    ensure_geo_collections()
    ensure_legal_collections()
    ensure_auth_collections()
    ensure_room_features_collections()
    ensure_lost_and_found_collections()
    ensure_hr_collections()
    ensure_expenses_collections()
    from src.app.modules.instay.routes import ensure_stay_collections
    ensure_stay_collections()
    ensure_hotel_permission_collections()
    ensure_hotels_collections()
    ensure_audit_indexes()
    ensure_outbox_collection()
    ensure_promotions_collection()
    ensure_scheduled_promotions_collection()
    process_pending_outbox(get_database())
    # Periodic outbox drainer: catches up on ``audit_log`` writes that failed
    # inline (rare; e.g. transient mongo blip). Daemon thread so uvicorn
    # shutdown tears down naturally without hanging.
    threading.Thread(
        target=process_pending_outbox_forever,
        args=(get_database(),),
        daemon=True,
    ).start()
    # Scheduled promotions queue: sends queued campaigns once ``send_at``
    # arrives. Daemon thread (same pattern as the outbox drainer).
    threading.Thread(
        target=process_due_scheduled_promotions_forever,
        args=(get_database(),),
        daemon=True,
    ).start()
    threading.Thread(target=refresh_kpis_background, daemon=True).start()
    # Periodic internal notifications for forgotten open cash shifts
    # (expired → block active; open_long → manager heads-up).
    from src.app.modules.reception.notifications import (
        sweep_shift_notifications_forever,
    )
    sweep_shift_notifications_forever()
    yield


app = create_app()
