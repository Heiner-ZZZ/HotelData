"""Sync canonical permissions for a given role_name from a definition map.

Usage:
    python scripts/sync_role_permissions.py             # sync all roles
    python scripts/sync_role_permissions.py maintenance  # sync only maintenance
"""

from __future__ import annotations

import sys

from pymongo import MongoClient, UpdateOne

MONGO_URI = "mongodb://localhost:27018"
DB_NAME = "hoteldata_hub"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": [
        "users.manage", "users.create", "users.read", "users.update", "users.delete",
        "roles.manage", "roles.create", "roles.read", "roles.update", "roles.delete",
        "reservations.manage", "reservations.create", "reservations.read",
        "reservations.update", "reservations.delete",
        "check-ins.manage", "check-ins.read", "check-outs.manage", "check-outs.read",
        "properties.manage", "properties.read", "properties.update",
        "hotels.manage", "hotels.read", "hotels.update",
        "rooms.manage", "rooms.read", "rooms.update",
        "rates.manage", "rates.read", "rates.update",
        "revenue.manage", "revenue.read",
        "reports.manage", "reports.read",
        "dashboard.manage", "dashboard.read",
        "housekeeping.manage", "housekeeping.create", "housekeeping.read",
        "housekeeping.update", "housekeeping.delete",
        "maintenance.manage", "maintenance.read", "maintenance.update",
        "charges.manage", "charges.read",
        "inventory.manage", "inventory.read",
        "hr.manage", "hr.create", "hr.read", "hr.update", "hr.delete",
        "billing.manage", "billing.read",
        "payments.manage", "payments.read",
        "shifts.manage", "shifts.create", "shifts.read", "shifts.update",
        "amenities.manage", "amenities.read",
        "promotions.manage", "promotions.read",
        "settings.manage", "settings.read",
        "audit.manage", "audit.read",
        "monitoring.manage", "monitoring.read",
        "etl.manage", "etl.read", "etl.execute",
        "account.manage", "account.read", "account.update",
        "search.manage", "search.read",
    ],
    "admin_sistema": [
        "users.manage", "roles.read", "dashboard.read",
        "etl.read", "etl.execute", "audit.read", "monitoring.read", "settings.read",
    ],
    "operador_datos": [
        "dashboard.read", "etl.read", "etl.execute", "audit.read", "monitoring.read",
    ],
    "auditor_datos": [
        "dashboard.read", "etl.read", "audit.read", "monitoring.read", "reports.read",
    ],
    "hotel_partner": [
        "dashboard.read", "hotels.manage", "properties.read", "rooms.read",
        "reservations.manage", "revenue.read",
        "promotions.read", "promotions.manage",
    ],
    "gerente_hotel": [
        "dashboard.read", "hotels.manage", "properties.read", "rooms.read",
        "reservations.manage", "revenue.read", "rates.read",
        "inventory.read", "promotions.read", "promotions.manage",
    ],
    "revenue_manager": [
        "dashboard.read", "revenue.manage", "rates.manage",
        "reservations.read", "inventory.read", "reports.read",
        "promotions.read", "promotions.manage",
    ],
    "marketing_hotelero": [
        "dashboard.read", "properties.read", "amenities.manage",
        "promotions.manage", "promotions.read", "revenue.read",
    ],
    "cliente": [
        "search.read", "account.read", "account.update",
        "reservations.read", "reservations.create",
        "billing.read", "payments.read",
    ],
    "maintenance": [
        "dashboard.read",
        "housekeeping.read", "housekeeping.update",
        "maintenance.manage",
        "inventory.read",
        "hr.read",
        "properties.read",
        "reservations.read",
    ],
}


def sync(role_name: str | None = None, uri: str = MONGO_URI, db_name: str = DB_NAME) -> None:
    client = MongoClient(uri)
    db = client[db_name]
    roles_to_sync = [role_name] if role_name else list(ROLE_PERMISSIONS)

    ops = []
    for rname in roles_to_sync:
        perms = ROLE_PERMISSIONS.get(rname)
        if perms is None:
            print(f"  ⚠  Unknown role {rname!r}, skipping")
            continue
        ops.append(
            UpdateOne(
                {"role_name": rname},
                {"$set": {"permissions": perms, "updated_at": None}},
            )
        )

    if ops:
        result = db.roles.bulk_write(ops)
        print(f"  ✓  Matched {result.matched_count}, modified {result.modified_count} role(s)")
    else:
        print("  -  Nothing to sync")

    if role_name:
        role = db.roles.find_one({"role_name": role_name}, {"permissions": 1})
        if role:
            print(f"  →  {role_name} permissions: {role.get('permissions', [])}")

    client.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    sync(target)
