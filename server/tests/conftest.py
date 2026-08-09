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

import atexit
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

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
    "navigation",  # seed_navigation() de los tests de invariante (catálogo vs BD)
    "email_verification_tokens",  # register-property verify codes (auth)
    # --- HR ---------------------------------------------------------------
    "employees",
    "employee_departments",
    "employee_documents",
    "employee_positions",
    "employee_shifts",
    # --- Control ETL ------------------------------------------------------
    "etl_executions",
    "data_quality_reports",
    "rejected_records",
    "search_logs",
    "system_catalogs",
    "system_currencies",  # catálogo de monedas (onboarding / pricing)
    "system_counters",    # contadores de secuencia (folios, etc.)
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
    "maintenance_financial_reconciliations",
    "room_status_history",
    "room_status_log",
    "additional_charges",
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
    "booking_room_guests",
    "manual_reservations",
    # --- Billing and invoices -------------------------------------------
    "reservation_invoices",
    "reservation_payments",
    "fact_reservation_invoices",
    "fact_reservation_payments",
    "payment_reconciliation_events",
    "hotel_domain_events",
    "fact_hotel_domain_events",
    "hotel_financial_aggregates",
    "refund_documents",
    "fact_refund_documents",
    "guest_folios",  # create_folio/post_to_folio/close_folio/list_folios (billing.service.folio)
    "folio_settlement_events",
    "fact_folio_settlement_events",
    "platform_earnings",
    # --- Reviews --------------------------------------------------------
    "reviews",
    "fact_reviews",
    # --- Hotel products + inventory (Fase 4 + Fase 6) ------------------
    "hotel_products",
    "fact_inventory",
    "chart_of_accounts",
    "journal_entries",
    # --- Expenses / ledger (Fase 5 + Fase 6) ----------------------------
    "expense_invoices",
    "expense_categories",
    "expense_budget",
    "ledger_transactions",
    # --- Auditoría (audit trail universal + transactional outbox) -------
    "audit_log",
    "outbox",
    # --- Log de notificaciones de email (reservations/notifications) ----
    "notification_log",
    # --- Pricing por bandas (APROBACION_HOTELES_Y_PRICING.md §6/§8) ----
    "pricing_plans",
    # --- Instay / guest portal -----------------------------------------
    "stay_sessions",
    "stay_service_requests",
    "stay_messages",
    "lost_and_found",
    # --- Reception (turnos de caja) ------------------------------------
    "reception_shifts",
    # --- Account / notificaciones / tracking ----------------------------
    "user_favorites",
    "notification_log",
    "click_events",
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


_ENSURES_RUN = False


def _run_module_ensures_once() -> None:
    """Run the module ensures exactly ONCE per pytest process.

    The ensures create collections + indexes (idempotent). After the first
    test they are pure no-ops in intent — but NOT in reality: some of them
    (e.g. ``ensure_hotel_profile_collections``) do an unconditional
    ``drop_index_safe("dim_hotels", "prop_id_1")`` + recreate on EVERY call.
    Running all 7 ensures per test turns into an index drop/create war
    (~hundreds of ``dropIndexes`` per minute) that adds lock contention to
    the shared mongo and delays/interrupts in-flight operations. Memoizing
    to once-per-process keeps the schema guarantee with zero churn.
    """
    global _ENSURES_RUN
    if _ENSURES_RUN:
        return
    _ENSURES_RUN = True
    from src.app.modules.hotels.collections import ensure_hotels_collections
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
    ensure_hotels_collections()
    ensure_revenue_collections()
    ensure_hotel_permission_collections()


def _acquire_test_db_lock() -> None:
    """Fail fast if another pytest process shares the test DB.

    Two pytest processes running concurrently against ``hoteldata_hub_test``
    silently corrupt each other: each test's ``delete_many`` cleanup wipes the
    OTHER process's seeded users/sessions/roles mid-flight, producing
    intermittent 401/403/duplicate-key failures that are impossible to
    reproduce in isolation. The lock turns that silent corruption into an
    explicit, actionable error. Tests only run inside the Linux server
    container, so ``fcntl`` is always available there.

    Alcance: el flock vive en ``/tmp`` del contenedor — protege a los procesos
    del MISMO contenedor (el caso real de este repo). No protege contra pytest
    desde otro contenedor/host.
    """
    try:
        import fcntl
        import time
    except ImportError:  # pragma: no cover - pytest desde host Windows sin fcntl
        logger.warning(
            "fcntl no disponible: sin lock de exclusión para la BD de test. "
            "No corras dos pytest a la vez contra hoteldata_hub_test."
        )
        return
    lock_path = "/tmp/hoteldata_test_db.lock"
    # Modo append (NO "w"): truncar el archivo destruiría el marcador de PID del
    # holder y rompería el chequeo de doble importación de abajo.

    # (``_release``), así que NO puede vivir en un context manager.
    lock_file = open(lock_path, "a+")  # noqa: SIM115
    # Breve reintento antes de fallar: un `docker compose exec` secuencial puede
    # arrancar el siguiente pytest mientras el anterior aún está cerrando su
    # event loop (pytest-asyncio) — solapamiento de fracciones de segundo que NO
    # es corrupción real. Una suite concurrente de verdad (minutos) agota la
    # ventana y recibe el error explícito.
    deadline = time.monotonic() + 15.0
    while True:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Estampar el PID del holder: permite detectar la RE-importación del
            # mismo archivo dentro del MISMO proceso (``from tests.conftest
            # import login`` carga conftest.py por segunda vez como módulo
            # distinto, y su segundo ``flock`` chocaría con el primero dando un
            # falso "lock en uso" — auto-deadlock). El segundo import lee su
            # propio PID y sigue sin re-adquirir.
            lock_file.seek(0)
            lock_file.truncate()
            lock_file.write(str(os.getpid()))
            lock_file.flush()
            break
        except OSError:
            try:
                lock_file.seek(0)
                raw = lock_file.read().strip()
                owner = int(raw) if raw else 0
            except (ValueError, OSError):
                # El archivo puede estar truncándose a la vez (otro import
                # compitiendo) — tratar como sin owner conocido.
                owner = 0
            if owner == os.getpid():
                # Ya lo tiene ESTE proceso vía una importación duplicada del
                # módulo conftest (conftest vs tests.conftest). No es contención
                # real: el primer flock sigue vivo hasta el exit del proceso.
                break
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Otro proceso pytest está corriendo contra la BD de test compartida "
                    f"({lock_path} en uso). Dos suites simultáneas se pisan los datos "
                    "(401/403/duplicate-key intermitentes). Espera a que el otro proceso "
                    "termine (o mátalo) y reintenta."
                ) from None
            time.sleep(0.25)

    def _release() -> None:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        finally:
            lock_file.close()

    atexit.register(_release)


_acquire_test_db_lock()


@pytest.fixture(autouse=True)
def _clean_collections(db):
    """Empty all test collections before each test for isolation.

    Uses `delete_many` instead of `drop_collection` (see comment below). The
    module ensures run once per process (``_run_module_ensures_once``), not
    per test: per-test runs turned into an index drop/create war.
    """
    # Limpieza por `delete_many` en vez de `drop_collection`: en un replica set,
    # el drop + recreación de ~30 índices por test (las ensures de abajo) genera
    # un backlog de idents "drop-pending" (WiredTiger ObjectIsBusy 314) que
    # hace que la PRIMERA escritura de la siguiente prueba caiga en una
    # colección aún en estado de dropping → inserts perdidos → 400/401
    # intermitentes (ej. "El país seleccionado no existe"). delete_many deja la
    # colección vacía (misma semántica de aislamiento) sin tocar el ciclo de
    # vida del ident ni los índices → las ensures pasan a ser no-ops reales.
    for collection_name in TEST_COLLECTIONS:
        db[collection_name].delete_many({})
    _run_module_ensures_once()
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
