"""Phase 1 — Seed comprehensive CRUD permission catalog.

Usage:
  docker compose -f infra/docker-compose.yml exec -T server python scripts/migrate_permissions_crud.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[mongo_database]


# ── Resource definitions ──
# Each resource has one or more actions.
# "manage" is a wildcard that implies all CRUD for that resource.
# "execute" is for ETL/data-pipeline operations.
PERMISSION_CATALOG = [
    # ── Core System ──
    ("users",       ["manage", "create", "read", "update", "delete"]),
    ("roles",       ["manage", "create", "read", "update", "delete"]),

    # ── Operations ──
    ("reservations",["manage", "create", "read", "update", "delete"]),
    ("check-ins",   ["manage", "create", "read", "update"]),
    ("check-outs",  ["manage", "create", "read", "update"]),
    ("in-stay",     ["manage", "create", "read", "update"]),

    # ── Property Management ──
    ("properties",  ["manage", "create", "read", "update", "delete"]),
    ("hotels",      ["manage", "create", "read", "update", "delete"]),
    ("rooms",       ["manage", "create", "read", "update", "delete"]),
    ("rates",       ["manage", "create", "read", "update", "delete"]),

    # ── Revenue & Analytics ──
    ("revenue",     ["manage", "read"]),
    ("reports",     ["manage", "read"]),
    ("dashboard",   ["manage", "read"]),

    # ── Housekeeping & Maintenance ──
    ("housekeeping",["manage", "create", "read", "update", "delete"]),
    ("maintenance", ["manage", "create", "read", "update", "delete"]),
    ("charges",     ["manage", "create", "read", "update", "delete"]),

    # ── Inventory ──
    ("inventory",   ["manage", "create", "read", "update", "delete"]),

    # ── HR ──
    ("hr",          ["manage", "create", "read", "update", "delete"]),

    # ── Billing & Finance ──
    ("billing",     ["manage", "create", "read", "update", "delete"]),
    ("payments",    ["manage", "create", "read", "update"]),

    # ── Content ──
    ("amenities",   ["manage", "create", "read", "update", "delete"]),
    ("promotions",  ["manage", "create", "read", "update", "delete"]),
    ("lost-found",  ["manage", "create", "read", "update", "delete"]),

    # ── System Admin ──
    ("settings",    ["manage", "read", "update"]),
    ("audit",       ["manage", "read"]),
    ("monitoring",  ["manage", "read"]),
    ("etl",         ["manage", "read", "execute"]),

    # ── Guest-facing ──
    ("account",     ["manage", "read", "update"]),
    ("search",      ["manage", "read"]),
]

DESCRIPTIONS = {
    # Core
    "users.manage": "Administrar usuarios — acceso total a gestión de cuentas",
    "users.create": "Crear nuevos usuarios",
    "users.read": "Ver lista y detalles de usuarios",
    "users.update": "Editar datos y roles de usuarios",
    "users.delete": "Eliminar usuarios",
    "roles.manage": "Administrar roles — acceso total a configuración de roles",
    "roles.create": "Crear nuevos roles",
    "roles.read": "Ver lista y matriz de roles/permisos",
    "roles.update": "Editar roles y sus permisos asignados",
    "roles.delete": "Eliminar roles",

    # Operations
    "reservations.manage": "Administrar reservas — acceso total",
    "reservations.create": "Crear nuevas reservas",
    "reservations.read": "Ver lista y detalle de reservas",
    "reservations.update": "Modificar reservas existentes",
    "reservations.delete": "Cancelar o eliminar reservas",
    "check-ins.manage": "Administrar check-ins — acceso total",
    "check-ins.create": "Registrar nuevos check-ins",
    "check-ins.read": "Ver lista de check-ins",
    "check-ins.update": "Modificar check-ins",
    "check-outs.manage": "Administrar check-outs — acceso total",
    "check-outs.create": "Registrar nuevos check-outs",
    "check-outs.read": "Ver lista de check-outs",
    "check-outs.update": "Modificar check-outs",
    "in-stay.manage": "Administrar in-stay — acceso total",
    "in-stay.create": "Crear pedidos/solicitudes durante estancia",
    "in-stay.read": "Ver pedidos activos durante estancia",
    "in-stay.update": "Modificar pedidos en estancia",

    # Properties
    "properties.manage": "Administrar propiedades — acceso total",
    "properties.create": "Registrar nuevas propiedades",
    "properties.read": "Ver catálogo y detalle de propiedades",
    "properties.update": "Editar datos de propiedades",
    "properties.delete": "Eliminar propiedades",
    "hotels.manage": "Administrar hoteles — acceso total a contenido y configuración",
    "hotels.create": "Crear contenido de hotel",
    "hotels.read": "Ver contenido y perfiles de hoteles",
    "hotels.update": "Editar contenido de hoteles",
    "hotels.delete": "Eliminar contenido de hoteles",
    "rooms.manage": "Administrar habitaciones — acceso total",
    "rooms.create": "Crear tipos de habitación y habitaciones físicas",
    "rooms.read": "Ver habitaciones y su configuración",
    "rooms.update": "Editar habitaciones",
    "rooms.delete": "Eliminar habitaciones",
    "rates.manage": "Administrar tarifas — acceso total",
    "rates.create": "Crear planes de tarifas y rate plans",
    "rates.read": "Ver tarifas y rate plans",
    "rates.update": "Editar tarifas",
    "rates.delete": "Eliminar tarifas",

    # Revenue
    "revenue.manage": "Administrar revenue — acceso total",
    "revenue.read": "Ver dashboards y reportes de revenue",
    "reports.manage": "Administrar reportes — acceso total",
    "reports.read": "Ver reportes del sistema",
    "dashboard.manage": "Administrar dashboard — acceso total",
    "dashboard.read": "Ver dashboard principal",

    # Housekeeping
    "housekeeping.manage": "Administrar housekeeping — acceso total",
    "housekeeping.create": "Crear tareas de limpieza",
    "housekeeping.read": "Ver tareas, dashboard y estado de habitaciones",
    "housekeeping.update": "Editar tareas y transiciones de estado",
    "housekeeping.delete": "Eliminar tareas de limpieza",
    "maintenance.manage": "Administrar mantenimiento — acceso total",
    "maintenance.create": "Crear órdenes de mantenimiento",
    "maintenance.read": "Ver órdenes y dashboard de mantenimiento",
    "maintenance.update": "Editar órdenes de mantenimiento",
    "maintenance.delete": "Eliminar órdenes de mantenimiento",
    "charges.manage": "Administrar cargos adicionales — acceso total",
    "charges.create": "Crear cargos adicionales",
    "charges.read": "Ver cargos registrados",
    "charges.update": "Editar cargos",
    "charges.delete": "Eliminar cargos",

    # Inventory
    "inventory.manage": "Administrar inventario — acceso total",
    "inventory.create": "Crear registros de inventario",
    "inventory.read": "Ver inventario y disponibilidad",
    "inventory.update": "Actualizar inventario",
    "inventory.delete": "Eliminar registros de inventario",

    # HR
    "hr.manage": "Administrar RRHH — acceso total",
    "hr.create": "Crear empleados (onboarding)",
    "hr.read": "Ver directorio, portal y datos de empleados",
    "hr.update": "Editar empleados",
    "hr.delete": "Eliminar empleados",

    # Billing
    "billing.manage": "Administrar facturación — acceso total",
    "billing.create": "Crear facturas y documentos",
    "billing.read": "Ver facturas e historial",
    "billing.update": "Editar facturas",
    "billing.delete": "Eliminar facturas",
    "payments.manage": "Administrar pagos — acceso total",
    "payments.create": "Registrar pagos",
    "payments.read": "Ver historial de pagos",
    "payments.update": "Modificar pagos",

    # Content
    "amenities.manage": "Administrar amenities — acceso total",
    "amenities.create": "Crear amenities y servicios",
    "amenities.read": "Ver catálogo de amenities",
    "amenities.update": "Editar amenities",
    "amenities.delete": "Eliminar amenities",
    "promotions.manage": "Administrar promociones — acceso total",
    "promotions.create": "Crear promociones",
    "promotions.read": "Ver promociones activas",
    "promotions.update": "Editar promociones",
    "promotions.delete": "Eliminar promociones",
    "lost-found.manage": "Administrar objetos perdidos — acceso total",
    "lost-found.create": "Registrar objeto perdido/encontrado",
    "lost-found.read": "Ver registros de lost & found",
    "lost-found.update": "Editar registros",
    "lost-found.delete": "Eliminar registros",

    # System
    "settings.manage": "Administrar configuración — acceso total",
    "settings.read": "Ver configuración del sistema",
    "settings.update": "Modificar configuración",
    "audit.manage": "Administrar auditoría — acceso total",
    "audit.read": "Ver logs y registros de auditoría",
    "monitoring.manage": "Administrar monitoreo — acceso total",
    "monitoring.read": "Ver dashboards de monitoreo",
    "etl.manage": "Administrar ETL — acceso total",
    "etl.read": "Ver estado y logs de ETL",
    "etl.execute": "Ejecutar pipelines ETL",

    # Guest
    "account.manage": "Administrar cuenta — acceso total",
    "account.read": "Ver perfil y datos de cuenta",
    "account.update": "Editar perfil y preferencias",
    "search.manage": "Administrar búsqueda — acceso total",
    "search.read": "Buscar hoteles y ver resultados",
}


def main() -> None:
    db = get_database()
    perms_coll = db["permissions"]
    created = 0
    updated = 0
    total = 0

    for resource, actions in PERMISSION_CATALOG:
        for action in actions:
            code = f"{resource}.{action}"
            description = DESCRIPTIONS.get(
                code, f"{'Administrar' if action == 'manage' else action.capitalize()} {resource}"
            )
            result = perms_coll.update_one(
                {"permission_code": code},
                {
                    "$set": {
                        "permission_code": code,
                        "description": description,
                        "is_system": True,
                        "updated_at": utc_now(),
                    },
                    "$setOnInsert": {"created_at": utc_now()},
                },
                upsert=True,
            )
            if result.upserted_id is not None:
                created += 1
            elif result.modified_count > 0:
                updated += 1
            total += 1

    total_existing = perms_coll.count_documents({})
    print(f"✓ Permission catalog seeded")
    print(f"  New:    {created}")
    print(f"  Updated:{updated}")
    print(f"  Total:  {total_existing} (catalog: {total} entries)")


if __name__ == "__main__":
    main()
