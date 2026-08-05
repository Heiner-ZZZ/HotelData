"""Shared fixtures for the web app test suite.

This conftest is intentionally additive: it never imports from `src.app.*`
modules in a way that would change production behavior. It:

1. Forces `MONGO_DATABASE` to a test-only database so the dev/prod DB is
   never touched by tests.
2. Drops a known set of collections before every test for isolation.
3. Provides seeded users (low-privilege `cliente` + `super_admin`) so
   auth and middleware tests can run end-to-end against the real Mongo.

Note on passwords: the passwords used here (`Secret123!` for
`cliente_test`, `AdminPass123!` for `admin_test`) are NOT the demo
passwords from `docs/ga03/usuarios_demo_ga03.md` (which are
`Cliente123*`, `Admin12345*`, etc.). The fixtures create their own
isolated users with known passwords so the tests are independent of
the demo seeding script.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

# IMPORTANT: set MONGO_DATABASE BEFORE any `src.app.*` import so the
# frozen Settings dataclass picks it up via `get_settings()`.
os.environ["MONGO_DATABASE"] = "hoteldata_hub_test"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext

from src.app.main import create_app
from src.database.connection import get_database


# Collections that the web app and middleware touch. Cleaned before each
# test. Adding a new collection to the app means adding it here.
#
# Source of truth: `docs/ga03/diseno_base_datos_ga03.md` (12 active
# dimensions + 2 legacy), `docs/ga03/modelo_seguridad_implementado.md`
# (2 security lookups: roles, permissions) and
# `docs/modelo_colecciones.md` (control + documentary collections).
TEST_COLLECTIONS = [
    # --- Security ---------------------------------------------------------
    "users",
    "user_sessions",
    "user_activity_logs",
    "roles",
    "permissions",
    "hotel_roles",
    "role_assignments",
    # --- HR ---------------------------------------------------------------
    "employees",
    "employee_departments",
    "employee_documents",
    "employee_shifts",
    # --- Control ETL ------------------------------------------------------
    "etl_executions",
    "data_quality_reports",
    "rejected_records",
    "search_logs",
    "system_catalogs",
    # --- Hechos -----------------------------------------------------------
    "fact_hotel_reservations",
    "fact_hotel_events",
    # --- Dimensiones activas (12) -----------------------------------------
    "dim_hotels",
    "dim_destinations",
    "dim_visitor_countries",
    "dim_sites",
    "dim_dates",
    "dim_promotions",
    "dim_click_status",
    "dim_reservation_status",
    "dim_occupancy_profile",
    "dim_stay_length_category",
    "dim_booking_window_category",
    "dim_price_category",
    # --- Dimensiones legadas (renombrar en MongoDB: dim_date → dim_date_legacy, dim_countries → dim_countries_legacy)
    "dim_countries_legacy",
    "dim_date_legacy",
    # --- Documentales (per diseno_base_datos_ga03.md) --------------------
    "hotels",
    "locations",
    "contacts",
    "websites",
    "facilities",
    "attractions",
    "hotel_quality",
    "dataset_container",
    # --- Contenido / propiedades del partner module ---------------------
    "hotel_content_pages",
    "hotel_images",
    "hotel_policies",
    "hotel_content_changes",
    "hotel_profile_changes",
    # --- Inventario y habitaciones --------------------------------------
    "room_types",
    "hotel_rooms",
    "room_inventory_calendar",
    "room_availability_blocks",
    "blackout_dates",
    # --- Housekeeping -----------------------------------------------------
    "housekeeping_tasks",
    "maintenance_tasks",
    # --- Tarifas y revenue ----------------------------------------------
    "rate_plans",
    "hotel_rate_calendar",
    "rate_rules",
    "promotion_campaigns",
    "coupon_codes",
    # --- Reservas --------------------------------------------------------
    "booking_orders",
    "booking_status_history",
    "booking_guests",
    "manual_reservations",
    # --- Billing and invoices -------------------------------------------
    "reservation_invoices",
    "reservation_payments",
    "fact_reservation_invoices",
    "fact_reservation_payments",
    # --- Reviews --------------------------------------------------------
    "reviews",
    # --- Hotel products + inventory (Fase 4 + Fase 6) ------------------
    "hotel_products",
    "fact_inventory",
    "chart_of_accounts",
    "journal_entries",
]


_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(password: str) -> str:
    return _pwd.hash(password)


def _seed_user(db, *, username: str, email: str, password: str, role: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    user_id = db.users.insert_one(
        {
            "username": username,
            "email": email,
            "display_name": username.replace("_", " ").title(),
            "password_hash": _hash_password(password),
            "primary_role": role,
            "is_active": True,
            "created_at": now,
        }
    ).inserted_id
    return {
        "user_id": str(user_id),
        "username": username,
        "email": email,
        "password": password,
        "primary_role": role,
    }


@pytest.fixture(scope="session")
def app():
    """The FastAPI app, built once per test session."""
    return create_app()


@pytest_asyncio.fixture
async def client(app):
    """An httpx AsyncClient wired to the app via ASGI transport.

    Cookies set by the server (e.g. `hoteldata_session` after login) are
    persisted on the client and sent on subsequent requests automatically.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
def db():
    """Direct access to the test Mongo database for setup/assertions."""
    return get_database()


@pytest.fixture(autouse=True)
def _clean_collections(db):
    """Drop all test collections before each test for isolation, then
    re-create partner module indexes so test writes see the same schema
    that production has at startup (the `lifespan` in `src/app/main.py`
    runs the partner bootstrap once per process; per-test isolation here
    drops the collections and therefore the indexes).
    """
    for collection_name in TEST_COLLECTIONS:
        db.drop_collection(collection_name)
    from src.app.modules.partner.services.bootstrap import (
        ensure_hotel_content_collections,
        ensure_hotel_profile_collections,
        ensure_inventory_collections,
        ensure_rate_collections,
    )
    from src.app.modules.revenue.service import ensure_revenue_collections
    from src.app.security.collections import ensure_hotel_permission_collections

    ensure_hotel_content_collections()
    ensure_hotel_profile_collections()
    ensure_inventory_collections()
    ensure_rate_collections()
    ensure_revenue_collections()
    ensure_hotel_permission_collections()
    yield


@pytest.fixture
def cliente_user(db):
    """A low-privilege user with role `cliente`.

    Returns a dict with the credentials the test can use to log in.
    """
    return _seed_user(
        db,
        username="cliente_test",
        email="cliente_test@example.com",
        password="Secret123!",
        role="cliente",
    )


@pytest.fixture
def admin_user(db):
    """A `super_admin` user (bypasses most ACL rules)."""
    return _seed_user(
        db,
        username="admin_test",
        email="admin_test@example.com",
        password="AdminPass123!",
        role="super_admin",
    )


async def login(client: AsyncClient, identifier: str, password: str) -> int:
    """POST /api/auth/login with JSON body; return the response status."""
    response = await client.post(
        "/api/auth/login",
        json={"identifier": identifier, "password": password},
    )
    return response.status_code
