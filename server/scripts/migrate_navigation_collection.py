"""Phase 3 — Seed navigation collection from NAVIGATION_BY_ROLE.

Extracts unique menu items from the hardcoded role-based navigation dict,
assigns a canonical required_permission and sort_order to each, and upserts
them into a new ``navigation`` collection.

Usage:
  docker compose -f infra/docker-compose.yml exec -T server python scripts/migrate_navigation_collection.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

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


# ── Canonical navigation catalog ──
# Derived from NAVIGATION_BY_ROLE but role-agnostic.
# Each item has a required_permission (minimum .read for visibility).
# sort_order groups by section: 100 = System, 200 = Management, 300 = Reports, 400 = Guest.
NAVIGATION_CATALOG = [
    # ── System Admin (100) ──
    {"label": "Usuarios",       "href": "/system/users",        "icon": "people",           "required_permission": "users.read",    "sort_order": 101},
    {"label": "Permisos",       "href": "/system/permissions",  "icon": "admin_panel_settings", "required_permission": "roles.read", "sort_order": 102},
    {"label": "Auditoría",      "href": "/system/audit",        "icon": "receipt_long",     "required_permission": "audit.read",    "sort_order": 103},
    {"label": "Monitoreo",      "href": "/system/monitoring",   "icon": "monitoring",       "required_permission": "monitoring.read", "sort_order": 104},
    {"label": "Notificaciones",  "href": "/system/notifications","icon": "notifications",    "required_permission": "settings.read", "sort_order": 105},
    {"label": "Monedas",        "href": "/system/currencies",   "icon": "payments",         "required_permission": "settings.read", "sort_order": 106},
    {"label": "BSC",            "href": "/system/bsc",          "icon": "bar_chart",        "required_permission": "dashboard.read","sort_order": 107},

    # ── Management / Operations (200) ──
    {"label": "Dashboard",      "href": "/management",           "icon": "dashboard",       "required_permission": "dashboard.read", "sort_order": 201},
    {"label": "Reservas",       "href": "/management/reservations","icon": "book_online",    "required_permission": "reservations.read", "sort_order": 202},
    {"label": "Disponibilidad", "href": "/management/availability","icon": "event_available","required_permission": "inventory.read",  "sort_order": 203},
    {"label": "Tarifas",        "href": "/management/rates",     "icon": "sell",            "required_permission": "rates.read",      "sort_order": 204},
    {"label": "Propiedades",    "href": "/management/properties","icon": "apartment",       "required_permission": "properties.read", "sort_order": 205},
    {"label": "Habitaciones",   "href": "/management/rooms",     "icon": "bed",             "required_permission": "rooms.read",      "sort_order": 206},
    {"label": "Amenities",      "href": "/management/amenities", "icon": "spa",             "required_permission": "amenities.read",  "sort_order": 207},

    # ── Housekeeping & Maintenance (300) ──
    {"label": "Housekeeping",   "href": "/management/housekeeping","icon": "cleaning_services","required_permission": "housekeeping.read","sort_order": 301},
    {"label": "Mantenimiento",  "href": "/management/housekeeping/maintenance","icon": "build","required_permission": "maintenance.read","sort_order": 302},
    {"label": "Cargos",         "href": "/management/housekeeping/charges","icon": "attach_money","required_permission": "charges.read",  "sort_order": 303},

    # ── HR (400) ──
    {"label": "RRHH",           "href": "/management/hr",        "icon": "badge",           "required_permission": "hr.read",         "sort_order": 401},
    {"label": "Mi Portal",      "href": "/management/hr/my-portal","icon": "person",        "required_permission": None,               "sort_order": 402},

    # ── Revenue & Reports (500) ──
    {"label": "Revenue",        "href": "/management/revenue",   "icon": "trending_up",     "required_permission": "revenue.read",    "sort_order": 501},
    {"label": "Reportes",       "href": "/management/reports",   "icon": "description",     "required_permission": "reports.read",    "sort_order": 502},
    {"label": "Facturación",    "href": "/management/billing",   "icon": "receipt",         "required_permission": "billing.read",    "sort_order": 503},

    # ── Guest-facing (600) ──
    {"label": "Buscar Hoteles", "href": "/search",               "icon": "search",          "required_permission": "search.read",     "sort_order": 601},
    {"label": "Mis Reservas",   "href": "/account/bookings",     "icon": "confirmation_number","required_permission": "reservations.read","sort_order": 602},
    {"label": "Mi Perfil",      "href": "/account/profile",      "icon": "account_circle",  "required_permission": "account.read",    "sort_order": 603},
    {"label": "Configuración",  "href": "/admin/global-settings","icon": "settings",        "required_permission": "settings.read",   "sort_order": 604},
]


def main() -> None:
    db = get_database()
    nav_coll = db["navigation"]

    # Create index
    nav_coll.create_index("sort_order")

    created = 0
    updated = 0

    for item in NAVIGATION_CATALOG:
        result = nav_coll.update_one(
            {"href": item["href"]},
            {
                "$set": {
                    "label": item["label"],
                    "href": item["href"],
                    "icon": item["icon"],
                    "required_permission": item.get("required_permission"),
                    "is_system": True,
                    "sort_order": item["sort_order"],
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            created += 1
            print(f"  + {item['label']} ({item['href']})")
        elif result.modified_count > 0:
            updated += 1
            print(f"  ~ {item['label']} ({item['href']})")

    total = nav_coll.count_documents({})
    print(f"\nNavigation catalog seeded: {created} new, {updated} updated, {total} total")


if __name__ == "__main__":
    main()
