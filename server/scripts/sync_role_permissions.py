"""Sync canonical permissions for a given role_name.

The role → permission matrix lives in ONE place: ``ROLE_PERMISSION_CODES`` in
``scripts/init_security_model_ga03.py``. This script no longer keeps its own
copy of that map — it imports the canonical one, so a later ``$set`` can never
drift from (and silently strip) permissions granted by the security-model init
script. ``ROLE_PERMISSIONS`` is kept as an alias for the historical name that
tests and ``_audit_permission_sources.py`` import.

Usage:
    python scripts/sync_role_permissions.py             # sync all roles
    python scripts/sync_role_permissions.py maintenance  # sync only maintenance
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Permitir ``python scripts/sync_role_permissions.py`` (el script vive en
# scripts/, así que ``scripts`` no está en sys.path por defecto).
SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from pymongo import MongoClient, UpdateOne

from scripts.init_security_model_ga03 import ROLE_PERMISSION_CODES

# Mismo contrato de conexión que get_database()/get_settings(): la URI y la BD
# vienen del entorno (compose inyecta MONGO_URI=mongodb://mongo:27018 dentro del
# contenedor). Los defaults cubren la ejecución directa desde el host.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27018")
DB_NAME = os.getenv("MONGO_DATABASE", "hoteldata_hub")

# Canonical single source of truth (single map, no duplication).
ROLE_PERMISSIONS: dict[str, list[str]] = ROLE_PERMISSION_CODES


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
