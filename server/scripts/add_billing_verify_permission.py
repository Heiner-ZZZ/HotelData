"""Backfill ``billing.verify`` into the DB (catalog + supervisor roles).

La cola de conciliación de suscripciones (``/api/admin/subscriptions``) gatea
sus rutas con ``require_permission("billing.verify")`` + el gate de supervisor.
El código nace en el catálogo canónico (``PERMISSION_CATALOG``) y en los mapas
canónico + sync para ``admin_sistema`` y ``gerente_hotel``, pero la BD puede
estar desincronizada (colección ``permissions`` sin el doc, o roles sin el
código). Este script replica el patrón de ``add_approve_permission.py``:

1. **Upsert** del código en ``permissions`` (misma forma canónica de
   ``upsert_permissions()``). Idempotente.
2. **$addToSet** (NUNCA $set — no pisa personalizaciones de la UI) otorga el
   código a ``admin_sistema`` y ``gerente_hotel``. ``super_admin`` no lo
   necesita: tiene bypass ``*.*``.

Run: python scripts/add_billing_verify_permission.py [--dry-run]
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from pymongo import MongoClient

from config.settings import get_settings
from scripts.init_security_model_ga03 import PERMISSION_CATALOG

VERIFY_CODE = "billing.verify"

# Roles supervisor que operan la cola de conciliación — paridad con
# ROLE_PERMISSION_CODES.
VERIFY_HOLDER_ROLES = ("admin_sistema", "gerente_hotel")

DRY_RUN = "--dry-run" in sys.argv


def utc_now() -> datetime:
    return datetime.now(UTC)


def verify_description() -> str:
    """Descripción canónica del código — fuente única: PERMISSION_CATALOG."""
    for code, desc in PERMISSION_CATALOG:
        if code == VERIFY_CODE:
            return desc
    raise ValueError(f"{VERIFY_CODE} no está en PERMISSION_CATALOG — revisa init_security_model_ga03.py")


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongo_database]
    print(f"DB: {db.name} ({'DRY-RUN' if DRY_RUN else 'aplicando'})")

    # 1. Catálogo — upsert con la forma canónica de upsert_permissions()
    existing = db.permissions.find_one({"permission_code": VERIFY_CODE})
    if DRY_RUN:
        print(
            f"  [catálogo] {VERIFY_CODE!r} {'existe — refrescaría descripción' if existing else 'NO existe — insertaría'} "
            f"({verify_description()})"
        )
    else:
        db.permissions.update_one(
            {"permission_code": VERIFY_CODE},
            {
                "$set": {
                    "permission_code": VERIFY_CODE,
                    "description": verify_description(),
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        print(f"  [catálogo] upsert {VERIFY_CODE!r} ok")

    # 2. Roles — $addToSet (aditivo, converge, no pisa personalizaciones)
    for role_name in VERIFY_HOLDER_ROLES:
        if DRY_RUN:
            role = db.roles.find_one({"role_name": role_name}, {"permissions": 1})
            current = set(role.get("permissions", [])) if role else set()
            missing = [c for c in (VERIFY_CODE,) if c not in current]
            print(f"  [rol {role_name}] agregaría: {missing}")
            continue
        grant = db.roles.update_one(
            {"role_name": role_name},
            {
                "$addToSet": {"permissions": VERIFY_CODE},
                "$set": {"updated_at": utc_now()},
            },
        )
        if grant.matched_count == 0:
            print(f"  [rol {role_name}] ⚠ NO EXISTE en la colección roles — verifica el nombre")
        else:
            print(f"  [rol {role_name}] matched={grant.matched_count} modified={grant.modified_count}")

    client.close()
    if DRY_RUN:
        print("Nada modificado (--dry-run).")


if __name__ == "__main__":
    main()
