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
    # Reports — granular táctico/estratégico (2026-08): cada informe con su
    # propio código + dos códigos de área (táctico/estratégico).
    ("reports.tactical.read", "Ver el área de informes tácticos (simples y compuestos)"),
    ("reports.strategic.read", "Ver el área de informes estratégicos"),
    ("reports.rates.adr.read", "Ver informe táctico ADR por fecha, tipo y canal (R1.2)"),
    ("reports.rates.calendar.read", "Ver informe táctico de calendario de tarifas"),
    ("reports.requests.read", "Ver informe táctico de solicitudes de servicio"),
    ("reports.billing.invoices.read", "Ver informe táctico de facturación por período (F1.4)"),
    ("reports.billing.payments.read", "Ver informe táctico de pagos por método (F1.5)"),
    ("reports.housekeeping.dashboard.read", "Ver dashboard simple de housekeeping"),
    ("reports.housekeeping.operations.read", "Ver informe compuesto de operaciones de housekeeping"),
    ("reports.housekeeping.matrix.read", "Ver matriz de estado de habitaciones (O1.2)"),
    ("reports.download", "Descargar/exportar informes (CSV/XLSX/PDF) — global a lo que ya puedes leer"),
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
        # Informes estratégicos (BSC) + descarga
        "reports.strategic.read", "reports.download",
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
        # Informes estratégicos + descarga (evidencia de auditoría)
        "reports.strategic.read", "reports.download",
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
        # Informes tácticos de revenue del propietario
        "reports.tactical.read", "reports.download",
        "reports.rates.adr.read", "reports.rates.calendar.read",
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
        # Informes: táctico completo + estratégico + descarga (nivel gerencial)
        "reports.tactical.read", "reports.strategic.read", "reports.download",
        "reports.rates.adr.read", "reports.rates.calendar.read", "reports.requests.read",
        "reports.billing.invoices.read", "reports.billing.payments.read",
        "reports.housekeeping.dashboard.read", "reports.housekeeping.operations.read",
        "reports.housekeeping.matrix.read",
        # Ancestros de dominio para ver los informes anidados
        "billing.read", "housekeeping.read",
    ],
    "revenue_manager": [
        "dashboard.read",
        "revenue.manage", "rates.manage",
        "reservations.read",
        "inventory.read",
        "reports.read",
        "promotions.read", "promotions.manage",
        # Informes tácticos de revenue + facturación + descarga
        "reports.tactical.read", "reports.download",
        "reports.rates.adr.read", "reports.rates.calendar.read",
        "reports.billing.invoices.read", "reports.billing.payments.read",
        "billing.read",
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
        # Informes tácticos de estado de habitaciones (operaciones + matriz)
        "reports.tactical.read",
        "reports.housekeeping.operations.read", "reports.housekeeping.matrix.read",
    ],
    "recepcionista": [
        "dashboard.read",
        "reservations.manage",
        "check-ins.manage",
        "check-outs.manage",
        "properties.read",
        "rooms.read",
        # Front desk money: registrar/reembolsar pagos, pagar facturas,
        # postings de folio, liquidación y cargos POS — todo estampado al turno
        # de caja. ``*.manage`` expande a create/read/update/delete (ver
        # src/app/security/permissions.py), así que cubre los .read históricos.
        "billing.manage",
        "payments.manage",
        "charges.manage",
        # Búsqueda de huéspedes para prefill rápido en recepción.
        "users.read",
        "shifts.read",
        "shifts.create",
        "shifts.update",
        "hr.read",
        "hr.portal.read", "hr.directory.read",
        "reviews.read",
        # Informe táctico de solicitudes (vista operativa, sin descarga)
        "reports.tactical.read", "reports.requests.read",
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
        # Informes tácticos de housekeeping (vista operativa, sin descarga)
        "reports.tactical.read",
        "reports.housekeeping.dashboard.read", "reports.housekeeping.operations.read",
        "reports.housekeeping.matrix.read",
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
        # Informe táctico de solicitudes (vista operativa)
        "reports.tactical.read", "reports.requests.read",
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


# ── Navigation catalog (data-driven tree: sidebar + horizontal sub-menus) ──
# Árbol normalizado (adjacency list): ``slug`` = identidad, ``parent_slug`` =
# jerarquía (None = raíz/sección), ``position`` = orden local entre hermanos,
# ``node_type`` = container|leaf, ``permission_code`` = gate por nodo. El MISMO
# árbol alimenta el sidebar vertical y el menú horizontal de informes.
NAVIGATION_CATALOG: list[dict[str, Any]] = [
    # ── Raíz: Gestión ──
    {"slug": "gestion", "label": "Gestión", "icon": "dashboard", "node_type": "container", "parent_slug": None, "position": 10, "permission_code": None, "href": None},
    #   ── Grupo: PMS ──
    {"slug": "gestion.pms", "label": "Dashboard", "icon": "dashboard", "node_type": "container", "parent_slug": "gestion", "position": 10, "permission_code": "dashboard.read", "href": "/management"},
    {"slug": "gestion.pms.propiedades", "label": "Propiedades", "icon": "apartment", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 10, "permission_code": "properties.read", "href": "/management/properties"},
    {"slug": "gestion.pms.habitaciones", "label": "Habitaciones", "icon": "bed", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 20, "permission_code": "rooms.read", "href": "/management/rooms"},
    {"slug": "gestion.pms.productos", "label": "Productos", "icon": "inventory_2", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 30, "permission_code": "properties.read", "href": "/management/products"},
    {"slug": "gestion.pms.amenities", "label": "Amenities", "icon": "spa", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 40, "permission_code": "amenities.read", "href": "/management/amenities"},
    {"slug": "gestion.pms.recepcion", "label": "Recepción", "icon": "calendar_month", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 50, "permission_code": "reservations.read", "href": "/management/recepcion"},
    {"slug": "gestion.pms.cajas-turnos", "label": "Cajas y Turnos", "icon": "point_of_sale", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 60, "permission_code": "shifts.read", "href": "/management/shifts"},
    {"slug": "gestion.pms.resenas", "label": "Reseñas", "icon": "reviews", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 70, "permission_code": "reviews.read", "href": "/management/reviews"},
    {"slug": "gestion.pms.auditoria", "label": "Auditoría Oper.", "icon": "receipt_long", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 80, "permission_code": "audit.read", "href": "/management/audit-log"},
    {"slug": "gestion.pms.perfil", "label": "Perfil", "icon": "account_circle", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 90, "permission_code": "account.read", "href": "/management/profile"},
    {"slug": "gestion.pms.equipo", "label": "Equipo y permisos", "icon": "admin_panel_settings", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 100, "permission_code": "hotel.manage_roles", "href": "/management/team-permissions"},
    {"slug": "gestion.pms.finanzas", "label": "Finanzas", "icon": "monetization_on", "node_type": "leaf", "parent_slug": "gestion.pms", "position": 110, "permission_code": "revenue.read", "href": "/management/expenses"},
    #   ── Grupo: Reservas (CRS) ──
    {"slug": "gestion.reservas", "label": "Reservas", "icon": "book_online", "node_type": "container", "parent_slug": "gestion", "position": 20, "permission_code": "reservations.read", "href": "/management/reservations"},
    {"slug": "gestion.reservas.disponibilidad", "label": "Disponibilidad", "icon": "event_available", "node_type": "leaf", "parent_slug": "gestion.reservas", "position": 10, "permission_code": "inventory.read", "href": "/management/availability"},
    {"slug": "gestion.reservas.tarifas", "label": "Tarifas", "icon": "sell", "node_type": "leaf", "parent_slug": "gestion.reservas", "position": 20, "permission_code": "rates.read", "href": "/management/rates"},
    #     ── Informes (menú horizontal de dashboards tácticos) ──
    {"slug": "gestion.reservas.informes", "label": "Informes", "icon": "monitoring", "node_type": "container", "parent_slug": "gestion.reservas", "position": 30, "permission_code": "reports.tactical.read", "href": None, "horizontal_menu": True},
    {"slug": "gestion.reservas.informes.adr", "label": "Dashboard ADR", "icon": "monitoring", "node_type": "leaf", "parent_slug": "gestion.reservas.informes", "position": 10, "permission_code": "reports.rates.adr.read", "href": "/management/rates/dashboard"},
    {"slug": "gestion.reservas.informes.calendario", "label": "Calendario Tarifas", "icon": "calendar_month", "node_type": "leaf", "parent_slug": "gestion.reservas.informes", "position": 20, "permission_code": "reports.rates.calendar.read", "href": "/management/rates/calendar"},
    {"slug": "gestion.reservas.informes.solicitudes", "label": "Dashboard Solicitudes", "icon": "room_service", "node_type": "leaf", "parent_slug": "gestion.reservas.informes", "position": 30, "permission_code": "reports.requests.read", "href": "/management/service-requests"},
    {"slug": "gestion.reservas.check-ins", "label": "Check-ins", "icon": "login", "node_type": "leaf", "parent_slug": "gestion.reservas", "position": 40, "permission_code": "check-ins.read", "href": "/management/check-ins"},
    {"slug": "gestion.reservas.estancias", "label": "Estancias Activas", "icon": "meeting_room", "node_type": "leaf", "parent_slug": "gestion.reservas", "position": 50, "permission_code": "reservations.read", "href": "/management/stay-inbox"},
    {"slug": "gestion.reservas.check-outs", "label": "Check-outs", "icon": "logout", "node_type": "leaf", "parent_slug": "gestion.reservas", "position": 60, "permission_code": "check-outs.read", "href": "/management/check-outs"},
    {"slug": "gestion.reservas.huespedes", "label": "Huéspedes", "icon": "people", "node_type": "leaf", "parent_slug": "gestion.reservas", "position": 70, "permission_code": "reservations.read", "href": "/management/guests"},
    {"slug": "gestion.reservas.politicas", "label": "Políticas", "icon": "policy", "node_type": "leaf", "parent_slug": "gestion.reservas", "position": 80, "permission_code": "properties.read", "href": "/management/policies"},
    #   ── Grupo: Housekeeping ──
    {"slug": "gestion.housekeeping", "label": "Housekeeping", "icon": "cleaning_services", "node_type": "container", "parent_slug": "gestion", "position": 30, "permission_code": "housekeeping.read", "href": "/management/housekeeping"},
    {"slug": "gestion.housekeeping.informes", "label": "Informes", "icon": "monitoring", "node_type": "container", "parent_slug": "gestion.housekeeping", "position": 10, "permission_code": "reports.tactical.read", "href": None, "horizontal_menu": True},
    {"slug": "gestion.housekeeping.informes.dashboard", "label": "Dashboard", "icon": "dashboard", "node_type": "leaf", "parent_slug": "gestion.housekeeping.informes", "position": 10, "permission_code": "reports.housekeeping.dashboard.read", "href": "/management/housekeeping/dashboard"},
    {"slug": "gestion.housekeeping.informes.operaciones", "label": "Operaciones", "icon": "analytics", "node_type": "leaf", "parent_slug": "gestion.housekeeping.informes", "position": 20, "permission_code": "reports.housekeeping.operations.read", "href": "/management/housekeeping/operations"},
    {"slug": "gestion.housekeeping.informes.matriz", "label": "Matriz", "icon": "grid_view", "node_type": "leaf", "parent_slug": "gestion.housekeeping.informes", "position": 30, "permission_code": "reports.housekeeping.matrix.read", "href": "/management/housekeeping/matrix"},
    {"slug": "gestion.housekeeping.mantenimiento", "label": "Mantenimiento", "icon": "build", "node_type": "leaf", "parent_slug": "gestion.housekeeping", "position": 20, "permission_code": "maintenance.read", "href": "/management/housekeeping/maintenance"},
    {"slug": "gestion.housekeeping.cargos", "label": "Cargos", "icon": "attach_money", "node_type": "leaf", "parent_slug": "gestion.housekeeping", "position": 30, "permission_code": "charges.read", "href": "/management/housekeeping/charges"},
    {"slug": "gestion.housekeeping.lost-found", "label": "Lost & Found", "icon": "search", "node_type": "leaf", "parent_slug": "gestion.housekeeping", "position": 40, "permission_code": "lost-found.read", "href": "/management/lost-and-found"},
    #   ── Grupo: RRHH ──
    {"slug": "gestion.rrhh", "label": "RRHH", "icon": "badge", "node_type": "container", "parent_slug": "gestion", "position": 40, "permission_code": "hr.read", "href": "/management/hr"},
    {"slug": "gestion.rrhh.portal", "label": "Mi Portal", "icon": "person", "node_type": "leaf", "parent_slug": "gestion.rrhh", "position": 10, "permission_code": "hr.portal.read", "href": "/management/hr/my-portal"},
    {"slug": "gestion.rrhh.directorio", "label": "Directorio RRHH", "icon": "groups", "node_type": "leaf", "parent_slug": "gestion.rrhh", "position": 20, "permission_code": "hr.directory.read", "href": "/management/hr/directory"},
    {"slug": "gestion.rrhh.onboarding", "label": "Onboarding", "icon": "person_add", "node_type": "leaf", "parent_slug": "gestion.rrhh", "position": 30, "permission_code": "hr.onboarding.create", "href": "/management/hr/onboarding"},
    {"slug": "gestion.rrhh.turnos", "label": "Turnos", "icon": "schedule", "node_type": "leaf", "parent_slug": "gestion.rrhh", "position": 40, "permission_code": "hr.shifts.read", "href": "/management/hr/shifts"},
    #   ── Grupo: Revenue ──
    {"slug": "gestion.revenue", "label": "Revenue", "icon": "trending_up", "node_type": "container", "parent_slug": "gestion", "position": 50, "permission_code": "revenue.read", "href": "/management/revenue"},
    {"slug": "gestion.revenue.reportes", "label": "Reportes", "icon": "description", "node_type": "leaf", "parent_slug": "gestion.revenue", "position": 10, "permission_code": "reports.read", "href": "/management/reports"},
    #   ── Grupo: Facturación ──
    {"slug": "gestion.billing", "label": "Facturación", "icon": "receipt", "node_type": "container", "parent_slug": "gestion", "position": 60, "permission_code": "billing.read", "href": "/management/billing"},
    {"slug": "gestion.billing.informes", "label": "Informes", "icon": "monitoring", "node_type": "container", "parent_slug": "gestion.billing", "position": 10, "permission_code": "reports.tactical.read", "href": None, "horizontal_menu": True},
    {"slug": "gestion.billing.informes.facturas", "label": "Dashboard", "icon": "monitoring", "node_type": "leaf", "parent_slug": "gestion.billing.informes", "position": 10, "permission_code": "reports.billing.invoices.read", "href": "/management/billing/dashboard"},
    {"slug": "gestion.billing.informes.pagos", "label": "Dashboard Pagos", "icon": "payments", "node_type": "leaf", "parent_slug": "gestion.billing.informes", "position": 20, "permission_code": "reports.billing.payments.read", "href": "/management/billing/payments-dashboard"},
    {"slug": "gestion.billing.pagos", "label": "Pagos", "icon": "payments", "node_type": "leaf", "parent_slug": "gestion.billing", "position": 20, "permission_code": "payments.read", "href": "/management/billing/payments"},
    # ── Raíz: Sistema ──
    {"slug": "sistema", "label": "Sistema", "icon": "admin_panel_settings", "node_type": "container", "parent_slug": None, "position": 20, "permission_code": None, "href": None},
    {"slug": "sistema.usuarios", "label": "Usuarios", "icon": "people", "node_type": "leaf", "parent_slug": "sistema", "position": 10, "permission_code": "users.read", "href": "/system/users"},
    {"slug": "sistema.permisos", "label": "Permisos", "icon": "admin_panel_settings", "node_type": "leaf", "parent_slug": "sistema", "position": 20, "permission_code": "roles.read", "href": "/system/permissions"},
    {"slug": "sistema.auditoria", "label": "Auditoría", "icon": "receipt_long", "node_type": "leaf", "parent_slug": "sistema", "position": 30, "permission_code": "audit.read", "href": "/system/audit"},
    {"slug": "sistema.monitoreo", "label": "Monitoreo", "icon": "monitoring", "node_type": "leaf", "parent_slug": "sistema", "position": 40, "permission_code": "monitoring.read", "href": "/system/monitoring"},
    {"slug": "sistema.notificaciones", "label": "Notificaciones", "icon": "notifications", "node_type": "leaf", "parent_slug": "sistema", "position": 50, "permission_code": "settings.read", "href": "/system/notifications"},
    {"slug": "sistema.monedas", "label": "Monedas", "icon": "payments", "node_type": "leaf", "parent_slug": "sistema", "position": 60, "permission_code": "settings.read", "href": "/system/currencies"},
    {"slug": "sistema.bsc", "label": "BSC", "icon": "bar_chart", "node_type": "leaf", "parent_slug": "sistema", "position": 70, "permission_code": "dashboard.read", "href": "/system/bsc"},
    {"slug": "sistema.config-global", "label": "Configuración", "icon": "settings", "node_type": "leaf", "parent_slug": "sistema", "position": 80, "permission_code": "settings.read", "href": "/admin/global-settings"},
    {"slug": "sistema.geo-catalogo", "label": "Geo-Catálogo", "icon": "map", "node_type": "leaf", "parent_slug": "sistema", "position": 90, "permission_code": "settings.read", "href": "/admin/geo-catalog"},
    # ── Raíz: Propietario ──
    {"slug": "propietario", "label": "Propietario", "icon": "assignment_ind", "node_type": "container", "parent_slug": None, "position": 30, "permission_code": None, "href": None},
    {"slug": "propietario.usuarios", "label": "Propietarios", "icon": "assignment_ind", "node_type": "leaf", "parent_slug": "propietario", "position": 10, "permission_code": "users.manage", "href": "/ownership/users"},
    # ── Raíz: Huésped ──
    {"slug": "huesped", "label": "Huésped", "icon": "person", "node_type": "container", "parent_slug": None, "position": 40, "permission_code": None, "href": None},
    {"slug": "huesped.buscar", "label": "Buscar Hoteles", "icon": "search", "node_type": "leaf", "parent_slug": "huesped", "position": 10, "permission_code": "search.read", "href": "/search"},
    {"slug": "huesped.reservas", "label": "Mis Reservas", "icon": "confirmation_number", "node_type": "leaf", "parent_slug": "huesped", "position": 20, "permission_code": "account.bookings.read", "href": "/account/bookings"},
    {"slug": "huesped.perfil", "label": "Mi Perfil", "icon": "account_circle", "node_type": "leaf", "parent_slug": "huesped", "position": 30, "permission_code": "account.read", "href": "/account/profile"},
]


def seed_navigation(navigation: Collection, permission_docs: dict[str, Any] | None = None) -> int:
    """Seed the navigation collection with the canonical tree.

    Si ``permission_docs`` (permission_code → doc con ``_id``) viene provisto,
    resuelve ``permission_code`` → ``permission_id`` (FK ObjectId) al sembrar.
    Sin él solo se guarda el código string y la FK se backfillea luego con los
    scripts de migración (``migrate_navigation_tree.py``).
    """
    navigation.create_index("slug", unique=True)
    navigation.create_index([("parent_slug", 1), ("position", 1)])
    seeded = 0
    for item in NAVIGATION_CATALOG:
        set_fields: dict[str, Any] = {
            **item,
            "is_system": True,
            "updated_at": utc_now(),
        }
        code = item.get("permission_code")
        if permission_docs is not None and code:
            perm_doc = permission_docs.get(code)
            if perm_doc is not None:
                set_fields["permission_id"] = perm_doc["_id"]
        result = navigation.update_one(
            {"slug": item["slug"]},
            {
                "$set": set_fields,
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            seeded += 1

    # ── Segunda pasada: resolver parent_id (self-FK ObjectId) ──
    # Igual que permission_id, el parent_id no se conoce hasta que el padre
    # existe en BD. Tras el upsert de todo el árbol, mapeamos slug → _id y
    # rellenamos la FK de cada nodo no raíz. Así el seed por sí solo produce
    # un árbol íntegro (ambas FKs resueltas) sin depender del script de
    # migración.
    slug_to_id = {doc["slug"]: doc["_id"] for doc in navigation.find({"slug": {"$exists": True}}, {"slug": 1})}
    for item in NAVIGATION_CATALOG:
        parent_slug = item.get("parent_slug")
        if parent_slug is None:
            continue
        parent_id = slug_to_id.get(parent_slug)
        if parent_id is not None:
            navigation.update_one(
                {"slug": item["slug"]},
                {"$set": {"parent_id": parent_id}},
            )
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
    permission_docs = upsert_permissions(collections["permissions"])
    roles_with_embedded_perms = embed_role_permissions(collections["roles"], role_docs)
    nav_seeded = seed_navigation(collections["navigation"], permission_docs)
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
