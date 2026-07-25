"""Add hotel staff roles (recepcionista, housekeeping, concierge) with hr.read."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from config.settings import get_settings
from pymongo import MongoClient


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ROLE_PERMISSIONS: dict[str, list[str]] = {
    "recepcionista": [
        "dashboard.read",
        "reservations.manage",
        "check-ins.manage",
        "check-outs.manage",
        "properties.read",
        "rooms.read",
        "billing.read",
        "payments.read",
        "hr.read",
    ],
    "housekeeping": [
        "dashboard.read",
        "housekeeping.read", "housekeeping.update",
        "maintenance.read",
        "inventory.read",
        "rooms.read",
        "hr.read",
    ],
    "concierge": [
        "dashboard.read",
        "reservations.read",
        "check-ins.read",
        "check-outs.read",
        "properties.read",
        "amenities.read",
        "hr.read",
    ],
}

ROLE_DISPLAY_NAMES: dict[str, str] = {
    "recepcionista": "Recepcionista",
    "housekeeping": "Housekeeping",
    "concierge": "Concierge",
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "recepcionista": "Operaciones de front desk: check-in, check-out y reservas.",
    "housekeeping": "Limpieza y estado de habitaciones.",
    "concierge": "Servicios y atención al huésped.",
}


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    inserted = 0
    updated = 0

    for role_name, permissions in ROLE_PERMISSIONS.items():
        result = db.roles.update_one(
            {"role_name": role_name},
            {
                "$set": {
                    "role_name": role_name,
                    "display_name": ROLE_DISPLAY_NAMES[role_name],
                    "description": ROLE_DESCRIPTIONS[role_name],
                    "permissions": permissions,
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {
                    "created_at": utc_now(),
                },
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        else:
            updated += 1

    print(f"Roles inserted: {inserted}, updated: {updated}")

    client.close()


if __name__ == "__main__":
    main()
