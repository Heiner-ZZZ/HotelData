from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

try:
    from passlib.context import CryptContext
except ImportError as exc:
    raise SystemExit(
        "Falta dependencia passlib[bcrypt]. Instala requirements.txt antes de ejecutar este script."
    ) from exc


SECURITY_COLLECTIONS = [
    "users",
    "roles",
    "permissions",
    "navigation",
    "user_sessions",
    "user_activity_logs",
]

BASE_ROLES = [
    ("super_admin", "Super administrador", "Acceso total para inicializacion y gobierno del sistema."),
    ("admin_sistema", "Administrador del sistema", "Administra configuracion operativa de la plataforma."),
    ("operador_datos", "Operador de datos", "Ejecuta y monitorea tareas de datos y ETL."),
    ("auditor_datos", "Auditor de datos", "Consulta auditoria, calidad y trazabilidad."),
    ("hotel_partner", "Hotel partner", "Gestiona informacion operativa de propiedades asociadas."),
    ("gerente_hotel", "Gerente de hotel", "Consulta rendimiento y operacion de propiedades."),
    ("revenue_manager", "Revenue manager", "Analiza tarifas, promociones e ingresos."),
    ("marketing_hotelero", "Marketing hotelero", "Consulta promocion y rendimiento comercial."),
    ("maintenance", "Mantenimiento", "Gestiona mantenimiento de habitaciones y propiedades."),
    ("recepcionista", "Recepcionista", "Operaciones de front desk: check-in, check-out y reservas."),
    ("housekeeping", "Housekeeping", "Limpieza y estado de habitaciones."),
    ("concierge", "Concierge", "Servicios y atención al huésped."),
    ("cliente", "Cliente", "Usuario final planificado para busqueda y reservas."),
]

# ── CRUD Permission Catalog (resource × action) ──
# Format: ("resource.action", "description")
# "manage" is a wildcard that expands to create/read/update/delete at runtime.
PERMISSION_CATALOG = [
    # Core System
    ("users.manage", "Administrar usuarios — acceso total a gestión de cuentas"),
    ("users.create", "Crear nuevos usuarios"),
    ("users.read", "Ver lista y detalles de usuarios"),
    ("users.update", "Editar datos y roles de usuarios"),
    ("users.delete", "Eliminar usuarios"),
    ("roles.manage", "Administrar roles — acceso total a configuración de roles"),
    ("roles.create", "Crear nuevos roles"),
    ("roles.read", "Ver lista y matriz de roles/permisos"),
    ("roles.update", "Editar roles y sus permisos asignados"),
    ("roles.delete", "Eliminar roles"),
    # Operations
    ("reservations.manage", "Administrar reservas — acceso total"),
    ("reservations.create", "Crear nuevas reservas"),
    ("reservations.read", "Ver lista y detalle de reservas"),
    ("reservations.update", "Modificar reservas existentes"),
    ("reservations.delete", "Cancelar o eliminar reservas"),
    ("check-ins.manage", "Administrar check-ins — acceso total"),
    ("check-ins.read", "Ver lista de check-ins"),
    ("check-outs.manage", "Administrar check-outs — acceso total"),
    ("check-outs.read", "Ver lista de check-outs"),
    # Properties
    ("properties.manage", "Administrar propiedades — acceso total"),
    ("properties.read", "Ver catálogo y detalle de propiedades"),
    ("properties.update", "Editar datos de propiedades"),
    ("hotels.manage", "Administrar hoteles — acceso total a contenido y configuración"),
    ("hotels.read", "Ver contenido y perfiles de hoteles"),
    ("hotels.update", "Editar contenido de hoteles"),
    ("properties.approve", "Aprobar/rechazar el registro de nuevos hoteles (cola de aprobación del admin)"),
    ("rooms.manage", "Administrar habitaciones — acceso total"),
    ("rooms.read", "Ver habitaciones y su configuración"),
    ("rooms.update", "Editar habitaciones"),
    ("rates.manage", "Administrar tarifas — acceso total"),
    ("rates.read", "Ver tarifas y rate plans"),
    ("rates.update", "Editar tarifas"),
    # Revenue
    ("revenue.manage", "Administrar revenue — acceso total"),
    ("revenue.read", "Ver dashboards y reportes de revenue"),
    ("reports.manage", "Administrar reportes — acceso total"),
    ("reports.read", "Ver reportes del sistema"),
    ("dashboard.manage", "Administrar dashboard — acceso total"),
    ("dashboard.read", "Ver dashboard principal"),
    # Housekeeping & Maintenance
    ("housekeeping.manage", "Administrar housekeeping — acceso total"),
    ("housekeeping.create", "Crear tareas de limpieza"),
    ("housekeeping.read", "Ver tareas, dashboard y estado de habitaciones"),
    ("housekeeping.update", "Editar tareas y transiciones de estado"),
    ("housekeeping.delete", "Eliminar tareas de limpieza"),
    ("maintenance.manage", "Administrar mantenimiento — acceso total"),
    ("maintenance.read", "Ver órdenes y dashboard de mantenimiento"),
    ("maintenance.update", "Editar órdenes de mantenimiento"),
    ("charges.manage", "Administrar cargos adicionales — acceso total"),
    ("charges.read", "Ver cargos registrados"),
    # Inventory
    ("inventory.manage", "Administrar inventario — acceso total"),
    ("inventory.read", "Ver inventario y disponibilidad"),
    # Inventory — granular cost (manager-only; recepcionista no ve cost_price)
    ("inventory.products.cost.read", "Ver costo unitario de productos en inventario (manager-only)"),
    ("inventory.products.cost.manage", "Editar costo unitario y registrar restock de productos (manager-only)"),
    # HR
    ("hr.manage", "Administrar RRHH — acceso total"),
    ("hr.create", "Crear empleados (onboarding)"),
    ("hr.read", "Ver directorio, portal y datos de empleados"),
    ("hr.update", "Editar empleados"),
    ("hr.delete", "Eliminar empleados"),
    # HR — granular por interfaz (2026-08): cada pantalla RRHH con su código.
    ("hr.portal.read", "Ver Mi Portal (auto-servicio del empleado)"),
    ("hr.directory.read", "Ver directorio, departamentos, documentos y datos de empleados"),
    ("hr.directory.manage", "Gestionar directorio: crear, editar y eliminar empleados, departamentos y documentos"),
    ("hr.onboarding.create", "Crear empleados (onboarding) y transferir permisos"),
    ("hr.shifts.read", "Ver turnos y horarios"),
    ("hr.shifts.manage", "Gestionar turnos: crear, editar, eliminar y registrar check-in/check-out"),
    # Billing
    ("billing.manage", "Administrar facturación — acceso total"),
    ("billing.read", "Ver facturas e historial"),
    ("payments.manage", "Administrar pagos — acceso total"),
    ("payments.read", "Ver historial de pagos"),
    # Shifts / Cash register
    ("shifts.manage", "Administrar turnos y cajas — acceso total (Control de Gerente)"),
    ("shifts.create", "Abrir nuevos turnos de caja"),
    ("shifts.read", "Ver estado y detalles de turnos de caja"),
    ("shifts.update", "Cerrar y declarar cuadre de caja (Shift close)"),
    # Content
    ("amenities.manage", "Administrar amenities — acceso total"),
    ("amenities.read", "Ver catálogo de amenities"),
    ("promotions.manage", "Administrar promociones — acceso total"),
    ("promotions.read", "Ver promociones activas"),
    # Reviews
    ("reviews.read", "Ver reseñas y su estado de moderación"),
    ("reviews.moderate", "Moderar y eliminar reseñas (aprobar/rechazar)"),
    ("lost-found.manage", "Administrar objetos perdidos — acceso total"),
    ("lost-found.create", "Registrar objeto perdido/encontrado"),
    ("lost-found.read", "Ver registros de lost & found"),
    ("lost-found.update", "Editar registros de lost & found"),
    ("lost-found.delete", "Eliminar registros de lost & found"),
    # System
    ("settings.manage", "Administrar configuración — acceso total"),
    ("settings.read", "Ver configuración del sistema"),
    ("audit.manage", "Administrar auditoría — acceso total"),
    ("audit.read", "Ver logs y registros de auditoría"),
    ("monitoring.manage", "Administrar monitoreo — acceso total"),
    ("monitoring.read", "Ver dashboards de monitoreo"),
    ("etl.manage", "Administrar ETL — acceso total"),
    ("etl.read", "Ver estado y logs de ETL"),
    ("etl.execute", "Ejecutar pipelines ETL"),
    # Hotel-scoped permissions (Fase 2 — RBAC por hotel)
    ("hotel.manage_roles", "Gestionar roles y permisos del equipo en un hotel"),
    # Guest-facing
    ("account.manage", "Administrar cuenta — acceso total"),
    ("account.read", "Ver perfil y datos de cuenta"),
    ("account.update", "Editar perfil y preferencias"),
    ("account.bookings.read", "Ver mis reservas — acceso a la página de reservas del huésped"),
    ("search.manage", "Administrar búsqueda — acceso total"),
    ("search.read", "Buscar hoteles y ver resultados"),
]

# ── Guest-facing codes (auto-servicio del huésped — sección "Cliente" del
#    editor de roles). super_admin conserva el bypass ``*.*`` de AUTH, pero NO
#    los tiene en el editor ni en su menú: Buscar Hoteles / Mis Reservas /
#    Mi Perfil son del huésped, no del administrador del sistema. Decisión
#    2026-08.
# KEEP IN SYNC: src/app/security/permissions.py (GUEST_PERMISSION_CODES).
GUEST_PERMISSION_CODES = frozenset({
    "account.manage",
    "account.read",
    "account.update",
    "account.bookings.read",
    "search.manage",
    "search.read",
})

# ── Role → embedded permissions (CRUD granular, stored directly on roles.permissions) ──
ROLE_PERMISSION_CODES: dict[str, list[str]] = {
    "super_admin": [
        code for code, _ in PERMISSION_CATALOG if code not in GUEST_PERMISSION_CODES
    ],
    "admin_sistema": [
        "users.manage", "roles.read",
        "dashboard.read",
        "etl.read", "etl.execute",
        "audit.read", "monitoring.read",
        "settings.read",
        "shifts.read",
        "hr.manage",
        "hr.portal.read", "hr.directory.read", "hr.directory.manage",
        "hr.onboarding.create", "hr.shifts.read", "hr.shifts.manage",
        "properties.approve",
    ],
    "operador_datos": [
        "dashboard.read",
        "etl.read", "etl.execute",
        "audit.read", "monitoring.read",
    ],
    "auditor_datos": [
        "dashboard.read",
        "etl.read",
        "audit.read", "monitoring.read",
        "reports.read",
    ],
    "hotel_partner": [
        "dashboard.read",
        "hotels.manage", "properties.read", "rooms.read",
        "reservations.manage",
        "revenue.read",
        "promotions.read", "promotions.manage",
        "hotel.manage_roles",
        # Reseñas: el ítem /management/reviews exige reviews.read (antes
        # properties.read); paridad para no perder la vista.
        "reviews.read",
    ],
    "gerente_hotel": [
        "dashboard.read",
        "hotels.manage", "properties.read", "rooms.read",
        "reservations.manage",
        "revenue.read", "rates.read",
        "inventory.read",
        "inventory.products.cost.read",
        "inventory.products.cost.manage",
        "promotions.read", "promotions.manage",
        "shifts.manage", "shifts.read",
        "hr.manage",
        "hr.portal.read", "hr.directory.read", "hr.directory.manage",
        "hr.onboarding.create", "hr.shifts.read", "hr.shifts.manage",
        "hotel.manage_roles",
        "properties.approve",
        "reviews.read",
    ],
    "revenue_manager": [
        "dashboard.read",
        "revenue.manage", "rates.manage",
        "reservations.read",
        "inventory.read",
        "reports.read",
        "promotions.read", "promotions.manage",
    ],
    "marketing_hotelero": [
        "dashboard.read",
        "properties.read",
        "amenities.manage", "promotions.manage", "promotions.read",
        "revenue.read",
        # Moderación de reseñas (PATCH/DELETE /api/reviews/{id} exige reviews.moderate;
        # el editor de roles exige reviews.read como dependencia de lectura).
        "reviews.read", "reviews.moderate",
    ],
    "maintenance": [
        "dashboard.read",
        "housekeeping.read", "housekeeping.update",
        "maintenance.manage",
        "inventory.read",
        "hr.read",
        "hr.portal.read", "hr.directory.read",
        "lost-found.read", "lost-found.update",
    ],
    "recepcionista": [
        "dashboard.read",
        "reservations.manage",
        "check-ins.manage",
        "check-outs.manage",
        "properties.read",
        "rooms.read",
        "billing.read",
        "payments.read",
        "shifts.read",
        "shifts.create",
        "shifts.update",
        "hr.read",
        "hr.portal.read", "hr.directory.read",
        "reviews.read",
    ],
    "housekeeping": [
        "dashboard.read",
        "housekeeping.read", "housekeeping.update",
        "maintenance.read",
        "inventory.read",
        "rooms.read",
        "hr.read",
        "hr.portal.read", "hr.directory.read",
        # Paridad con housekeeping.read/update — el módulo lost & found acepta
        # lost-found.* O housekeeping.* (require_any_permission).
        "lost-found.read", "lost-found.update",
    ],
    "concierge": [
        "dashboard.read",
        "reservations.read",
        "check-ins.read",
        "check-outs.read",
        "properties.read",
        "amenities.read",
        "hr.read",
        "hr.portal.read", "hr.directory.read",
    ],
    "cliente": [
        "search.read",
        "account.read", "account.update",
        "account.bookings.read",
        "reservations.read", "reservations.create",
        "billing.read", "payments.read",
    ],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[mongo_database]


def create_indexes(collections: dict[str, Collection]) -> None:
    """Idempotently create required indexes. Tolerates MongoDB code 85 (IndexOptionsConflict)
    and 86 (IndexKeySpecsConflict): when an equivalent key spec already exists under a
    different name (e.g., custom-named indexes from prior runs), skip silently instead
    of failing the whole script. Re-runs of this script are safe.
    """

    def _safe_create(coll: Collection, key, **opts) -> None:
        try:
            coll.create_index(key, **opts)
        except OperationFailure as exc:
            if exc.code in (85, 86):  # benign: equivalent index already exists
                return
            raise

    _safe_create(collections["users"], "email", unique=True)
    _safe_create(collections["users"], "username", unique=True)
    _safe_create(collections["roles"], "role_name", unique=True)
    _safe_create(collections["permissions"], "permission_code", unique=True)
    _safe_create(collections["user_sessions"], "session_token", unique=True, sparse=True)
    _safe_create(collections["user_sessions"], "user_id")
    _safe_create(collections["user_activity_logs"], "event_key", unique=True, sparse=True)
    _safe_create(collections["user_activity_logs"], [("created_at", -1)])


def upsert_roles(roles: Collection) -> dict[str, Any]:
    role_docs: dict[str, Any] = {}
    for role_name, display_name, description in BASE_ROLES:
        roles.update_one(
            {"role_name": role_name},
            {
                "$set": {
                    "role_name": role_name,
                    "display_name": display_name,
                    "description": description,
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        role_docs[role_name] = roles.find_one({"role_name": role_name})
    return role_docs


def upsert_permissions(permissions: Collection) -> dict[str, Any]:
    permission_docs: dict[str, Any] = {}
    for permission_code, description in PERMISSION_CATALOG:
        permissions.update_one(
            {"permission_code": permission_code},
            {
                "$set": {
                    "permission_code": permission_code,
                    "description": description,
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        permission_docs[permission_code] = permissions.find_one({"permission_code": permission_code})
    return permission_docs


def embed_role_permissions(
    roles: Collection,
    role_docs: dict[str, Any],
) -> int:
    """Write permissions directly into ``roles.permissions`` embedded array.

    """
    updated = 0
    for role_name, permission_codes in ROLE_PERMISSION_CODES.items():
        role = role_docs.get(role_name)
        if not role:
            continue
        roles.update_one(
            {"_id": role["_id"]},
            {"$set": {"permissions": permission_codes, "updated_at": utc_now()}},
        )
        updated += 1
    return updated


# ── Navigation catalog (data-driven sidebar menu) ──
NAVIGATION_CATALOG: list[dict[str, Any]] = [
    {"label": "Usuarios",       "href": "/system/users",        "icon": "people",           "required_permission": "users.read",    "sort_order": 101},
    {"label": "Permisos",       "href": "/system/permissions",  "icon": "admin_panel_settings", "required_permission": "roles.read", "sort_order": 102},
    {"label": "Auditoría",      "href": "/system/audit",        "icon": "receipt_long",     "required_permission": "audit.read",    "sort_order": 103},
    {"label": "Monitoreo",      "href": "/system/monitoring",   "icon": "monitoring",       "required_permission": "monitoring.read", "sort_order": 104},
    {"label": "Notificaciones",  "href": "/system/notifications","icon": "notifications",    "required_permission": "settings.read", "sort_order": 105},
    {"label": "Monedas",        "href": "/system/currencies",   "icon": "payments",         "required_permission": "settings.read", "sort_order": 106},
    {"label": "BSC",            "href": "/system/bsc",          "icon": "bar_chart",        "required_permission": "dashboard.read","sort_order": 107},
    {"label": "Dashboard",      "href": "/management",           "icon": "dashboard",       "required_permission": "dashboard.read", "section": "PMS","is_section_header": True,"sort_order": 201},
    {"label": "Reservas",       "href": "/management/reservations","icon": "book_online",    "required_permission": "reservations.read","section": "CRS","is_section_header": True,"sort_order": 202},
    {"label": "Disponibilidad", "href": "/management/availability","icon": "event_available","required_permission": "inventory.read",  "section": "CRS","sort_order": 203},
    {"label": "Tarifas",        "href": "/management/rates",     "icon": "sell",            "required_permission": "rates.read",      "section": "CRS","sort_order": 204},
    {"label": "Dashboard ADR",  "href": "/management/rates/dashboard","icon": "monitoring",   "required_permission": "rates.read",      "section": "CRS","sort_order": 204.5},
    {"label": "Calendario Tarifas","href": "/management/rates/calendar","icon": "calendar_month","required_permission": "rates.read",    "section": "CRS","sort_order": 204.6},
    {"label": "Propiedades",    "href": "/management/properties","icon": "apartment",       "required_permission": "properties.read", "section": "PMS","sort_order": 205},
    {"label": "Habitaciones",   "href": "/management/rooms",     "icon": "bed",             "required_permission": "rooms.read",      "section": "PMS","sort_order": 206},
    {"label": "Productos",      "href": "/management/products",  "icon": "inventory_2",     "required_permission": "properties.read", "section": "PMS","sort_order": 207},
    {"label": "Amenities",      "href": "/management/amenities", "icon": "spa",             "required_permission": "amenities.read",  "section": "PMS","sort_order": 208},
    {"label": "Recepción",      "href": "/management/recepcion",  "icon": "calendar_month",  "required_permission": "reservations.read","section": "PMS","sort_order": 209},
    {"label": "Cajas y Turnos", "href": "/management/shifts",     "icon": "point_of_sale",  "required_permission": "shifts.read",     "section": "PMS","sort_order": 210},
    {"label": "Dashboard Solicitudes","href": "/management/service-requests","icon": "room_service","required_permission": "reservations.read","section": "CRS","sort_order": 210.5},
    {"label": "Check-ins",      "href": "/management/check-ins",  "icon": "login",           "required_permission": "check-ins.read",  "section": "CRS","sort_order": 211},
    {"label": "Estancias Activas","href": "/management/stay-inbox","icon": "meeting_room",   "required_permission": "reservations.read","section": "CRS","sort_order": 212},
    {"label": "Check-outs",     "href": "/management/check-outs", "icon": "logout",          "required_permission": "check-outs.read", "section": "CRS","sort_order": 213},
    {"label": "Huéspedes",      "href": "/management/guests",     "icon": "people",          "required_permission": "reservations.read","section": "CRS","sort_order": 214},
    {"label": "Políticas",      "href": "/management/policies",   "icon": "policy",          "required_permission": "properties.read", "section": "CRS","sort_order": 215},
    {"label": "Reseñas",        "href": "/management/reviews",    "icon": "reviews",         "required_permission": "reviews.read", "section": "PMS","sort_order": 216},
    {"label": "Auditoría Oper.","href": "/management/audit-log",  "icon": "receipt_long",    "required_permission": "audit.read",      "section": "PMS","sort_order": 217},
    {"label": "Perfil",         "href": "/management/profile",    "icon": "account_circle",  "required_permission": "account.read",    "section": "PMS","sort_order": 218},
    {"label": "Equipo y permisos","href": "/management/team-permissions","icon": "admin_panel_settings","required_permission": "hotel.manage_roles","section": "PMS","sort_order": 219},
    {"label": "Housekeeping",   "href": "/management/housekeeping","icon": "cleaning_services","required_permission": "housekeeping.read","section": "Housekeeping","is_section_header": True,"sort_order": 301},
    {"label": "Mantenimiento",  "href": "/management/housekeeping/maintenance","icon": "build","required_permission": "maintenance.read","section": "Housekeeping","sort_order": 302},
    {"label": "Cargos",         "href": "/management/housekeeping/charges","icon": "attach_money","required_permission": "charges.read","section": "Housekeeping","sort_order": 303},
    {"label": "Lost & Found",   "href": "/management/lost-and-found","icon": "search",          "required_permission": "lost-found.read","section": "Housekeeping","sort_order": 304},
    {"label": "RRHH",           "href": "/management/hr",        "icon": "badge",           "required_permission": "hr.read",         "section": "RRHH","is_section_header": True,"sort_order": 401},
    {"label": "Mi Portal",      "href": "/management/hr/my-portal","icon": "person",        "required_permission": "hr.portal.read",  "section": "RRHH","sort_order": 402},
    {"label": "Directorio RRHH","href": "/management/hr/directory","icon": "groups",        "required_permission": "hr.directory.read","section": "RRHH","sort_order": 403},
    {"label": "Onboarding",     "href": "/management/hr/onboarding","icon": "person_add",    "required_permission": "hr.onboarding.create","section": "RRHH","sort_order": 404},
    {"label": "Turnos",         "href": "/management/hr/shifts",  "icon": "schedule",        "required_permission": "hr.shifts.read", "section": "RRHH","sort_order": 405},
    {"label": "Revenue",        "href": "/management/revenue",   "icon": "trending_up",     "required_permission": "revenue.read",    "section": "Revenue","is_section_header": True,"sort_order": 501},
    {"label": "Reportes",       "href": "/management/reports",   "icon": "description",     "required_permission": "reports.read",    "section": "Revenue","sort_order": 502},
    {"label": "Facturación",    "href": "/management/billing",   "icon": "receipt",         "required_permission": "billing.read",    "section": "Billing","is_section_header": True,"sort_order": 503},
    {"label": "Pagos",          "href": "/management/billing/payments","icon": "payments",      "required_permission": "payments.read",   "section": "Billing","sort_order": 504},
    {"label": "Dashboard",      "href": "/management/billing/dashboard","icon": "monitoring",  "required_permission": "billing.read",    "section": "Billing","sort_order": 504.5},
    {"label": "Dashboard Pagos","href": "/management/billing/payments-dashboard","icon": "payments","required_permission": "payments.read","section": "Billing","sort_order": 505},
    {"label": "Finanzas",       "href": "/management/expenses",   "icon": "monetization_on", "required_permission": "revenue.read",    "section": "PMS","sort_order": 505.5},
    {"label": "Buscar Hoteles", "href": "/search",               "icon": "search",          "required_permission": "search.read",     "sort_order": 601},
    {"label": "Mis Reservas",   "href": "/account/bookings",     "icon": "confirmation_number","required_permission": "account.bookings.read","sort_order": 602},
    {"label": "Mi Perfil",      "href": "/account/profile",      "icon": "account_circle",  "required_permission": "account.read",    "sort_order": 603},
    {"label": "Configuración",  "href": "/admin/global-settings","icon": "settings",        "required_permission": "settings.read",   "sort_order": 604},
    {"label": "Geo-Catálogo",   "href": "/admin/geo-catalog",    "icon": "map",             "required_permission": "settings.read",   "sort_order": 605},
    {"label": "Propietarios",   "href": "/ownership/users",      "icon": "assignment_ind",  "required_permission": "users.manage",    "sort_order": 701},
]


def seed_navigation(navigation: Collection) -> int:
    """Seed the navigation collection with canonical menu items."""
    navigation.create_index("sort_order")
    seeded = 0
    for item in NAVIGATION_CATALOG:
        result = navigation.update_one(
            {"href": item["href"]},
            {
                "$set": {
                    **item,
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            seeded += 1
    return seeded


def ensure_superadmin(users: Collection, role_docs: dict[str, Any]) -> dict[str, Any]:
    password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    super_admin_role = role_docs["super_admin"]
    existing_user = users.find_one({"$or": [{"username": "superadmin"}, {"email": "admin@hoteldata.local"}]})
    if existing_user:
        return {"created": False, "user_id": str(existing_user["_id"])}

    password_hash = password_context.hash("Admin12345*")
    result = users.insert_one(
        {
            "username": "superadmin",
            "email": "admin@hoteldata.local",
            "password_hash": password_hash,
            "temporary_password": True,
            "must_change_password": True,
            "is_active": True,
            "primary_role": "super_admin",
            "primary_role_id": super_admin_role["_id"],
            "email_verified": True,
            "role_ids": [super_admin_role["_id"]],
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "created_by": "scripts/init_security_model_ga03.py",
        }
    )
    return {"created": True, "user_id": str(result.inserted_id)}


def register_activity(user_activity_logs: Collection, superadmin_result: dict[str, Any]) -> None:
    user_activity_logs.update_one(
        {"event_key": "ga03_security_model_initialized"},
        {
            "$set": {
                "event_key": "ga03_security_model_initialized",
                "action": "security_model.initialized",
                "module": "security",
                "details": {
                    "script": "scripts/init_security_model_ga03.py",
                    "superadmin_created": superadmin_result["created"],
                    "collections": SECURITY_COLLECTIONS,
                },
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )


def collection_counts(collections: dict[str, Collection]) -> dict[str, int]:
    return {name: collection.count_documents({}) for name, collection in collections.items()}


def main() -> None:
    db = get_database()
    collections = {name: db[name] for name in SECURITY_COLLECTIONS}
    create_indexes(collections)

    role_docs = upsert_roles(collections["roles"])
    permissions_seeded = upsert_permissions(collections["permissions"])
    roles_with_embedded_perms = embed_role_permissions(collections["roles"], role_docs)
    nav_seeded = seed_navigation(collections["navigation"])
    superadmin_result = ensure_superadmin(collections["users"], role_docs)
    register_activity(collections["user_activity_logs"], superadmin_result)

    result = {
        "ok": True,
        "database": db.name,
        "created_or_verified_collections": SECURITY_COLLECTIONS,
        "roles_configured": len(BASE_ROLES),
        "permissions_configured": len(PERMISSION_CATALOG),
        "roles_with_embedded_permissions": roles_with_embedded_perms,
        "navigation_items_seeded": nav_seeded,
        "superadmin": superadmin_result,
        "counts": collection_counts(collections),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
