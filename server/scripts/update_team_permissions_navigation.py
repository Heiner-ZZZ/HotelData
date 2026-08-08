"""Add the Fase 2 UI nav item 'Equipo y permisos' (/management/team-permissions).

La vista consume /api/management/hotels/{prop_id}/roles + /assignments, ambos
protegidos con ``hotel.manage_roles``. El ítem de navegación usa esa misma
``required_permission`` para que solo lo vean hotel_partner / gerente_hotel
con el permiso en su rol global.

Idempotente; acepta ``--dry-run``. Replica la entrada del ``NAVIGATION_CATALOG``
de ``scripts/init_security_model_ga03.py`` (mantener en sync).

Run: python scripts/update_team_permissions_navigation.py [--dry-run]
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from pymongo import MongoClient

from config.settings import get_settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


NAV_ITEM = {
    "href": "/management/team-permissions",
    "label": "Equipo y permisos",
    "icon": "admin_panel_settings",
    "required_permission": "hotel.manage_roles",
    "section": "PMS",
    "is_system": True,
    "sort_order": 219,
}

DRY_RUN = "--dry-run" in sys.argv


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    existing = db.navigation.find_one({"href": NAV_ITEM["href"]}, {"_id": 1})
    action = "would upsert" if DRY_RUN else "upserting"
    if existing:
        action = "would update" if DRY_RUN else "updating"
    print(f"[{action}] {NAV_ITEM['label']} ({NAV_ITEM['href']})")

    if not DRY_RUN:
        result = db.navigation.update_one(
            {"href": NAV_ITEM["href"]},
            {
                "$set": {**NAV_ITEM, "updated_at": utc_now()},
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        print(f"  matched={result.matched_count}, upserted={result.upserted_id is not None}")

    client.close()


if __name__ == "__main__":
    main()
