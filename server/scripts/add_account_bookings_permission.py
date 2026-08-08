"""Backfill ``account.bookings.read`` into the dev DB (catalog + roles + nav).

El ítem "Mis Reservas" (``/account/bookings``) estaba gateado por
``reservations.read`` (permiso de staff en la caja "Gestión · Reservas"), por lo
que la caja **Cliente** del editor de roles no podía controlarlo. Este permiso
dedicado de huésped nace en el catálogo canónico (``PERMISSION_CATALOG`` de
``scripts/init_security_model_ga03.py``) y en los mapas canónico + sync para
``cliente`` y ``super_admin``. ``cliente`` CONSERVA ``reservations.read`` porque
el API del huésped sigue exigiendo ``reservations.*``.

Este script (convergente, idempotente — mismo patrón que ``add_approve_permission.py``):

1. **Upsert** del código en ``permissions`` replicando ``upsert_permissions()``.
2. **$addToSet** del código a los roles holder (``cliente`` y ``super_admin``).
3. **$pull** del código a CUALQUIER otro rol que lo tenga de más — converge al
   estado canónico sin pisar personalizaciones de otros permisos. Decisión
   2026-08: "Mis Reservas" es auto-servicio del huésped; revenue_manager y
   concierge NO deben tenerlo.
4. **Update** del ítem de navegación ``/account/bookings``:
   ``required_permission`` → ``account.bookings.read`` y refresca
   ``permission_id`` (ObjectId de la colección ``permissions``) para mantener
   la traza que ``migrate_navigation_permission_id.py`` dejó.

Mantener en sync con ROLE_PERMISSION_CODES (init) y ROLE_PERMISSIONS (sync).

Run: python scripts/add_account_bookings_permission.py [--dry-run]
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
from scripts.init_security_model_ga03 import PERMISSION_CATALOG

BOOKINGS_CODE = "account.bookings.read"

# Roles que deben ver el ítem "Mis Reservas" — paridad con ROLE_PERMISSION_CODES.
# "Mis Reservas" es auto-servicio del huésped: solo cliente y super_admin.
# Cualquier otro rol que lo tenga (p. ej. tras un grant manual) se revoca con $pull.
BOOKINGS_HOLDER_ROLES = ("cliente", "super_admin")

# Ítem de navegación que pasa de reservations.read a account.bookings.read.
BOOKINGS_NAV_HREF = "/account/bookings"

DRY_RUN = "--dry-run" in sys.argv


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def bookings_description() -> str:
    """Descripción canónica del código — fuente única: PERMISSION_CATALOG.
    Si el código desaparece del catálogo, el backfill falla alto en vez de
    sembrar una descripción hardcodeada que deriva del catálogo."""
    for code, desc in PERMISSION_CATALOG:
        if code == BOOKINGS_CODE:
            return desc
    raise ValueError(f"{BOOKINGS_CODE} no está en PERMISSION_CATALOG — revisa init_security_model_ga03.py")


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongo_database]
    print(f"DB: {db.name} ({'DRY-RUN' if DRY_RUN else 'aplicando'})")

    # 1. Catálogo — upsert con la forma canónica de upsert_permissions()
    existing = db.permissions.find_one({"permission_code": BOOKINGS_CODE})
    if DRY_RUN:
        print(
            f"  [catálogo] {BOOKINGS_CODE!r} {'existe — refrescaría descripción' if existing else 'NO existe — insertaría'} "
            f"({bookings_description()})"
        )
    else:
        db.permissions.update_one(
            {"permission_code": BOOKINGS_CODE},
            {
                "$set": {
                    "permission_code": BOOKINGS_CODE,
                    "description": bookings_description(),
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        print(f"  [catálogo] upsert {BOOKINGS_CODE!r} ok")

    # 2a. Roles holder — $addToSet (aditivo, no pisa personalizaciones)
    for role_name in BOOKINGS_HOLDER_ROLES:
        if DRY_RUN:
            role = db.roles.find_one({"role_name": role_name}, {"permissions": 1})
            current = set(role.get("permissions", [])) if role else set()
            missing = [c for c in (BOOKINGS_CODE,) if c not in current]
            print(f"  [rol {role_name}] agregaría: {missing}")
            continue
        grant = db.roles.update_one(
            {"role_name": role_name},
            {
                "$addToSet": {"permissions": BOOKINGS_CODE},
                "$set": {"updated_at": utc_now()},
            },
        )
        if grant.matched_count == 0:
            print(f"  [rol {role_name}] ⚠ NO EXISTE en la colección roles — verifica el nombre")
        else:
            print(f"  [rol {role_name}] matched={grant.matched_count} modified={grant.modified_count}")

    # 2b. Roles no-holder — $pull (convergencia: revoca grants fuera del mapa)
    revoked = db.roles.find({"permissions": BOOKINGS_CODE, "role_name": {"$nin": list(BOOKINGS_HOLDER_ROLES)}})
    stale_roles = [r["role_name"] for r in revoked]
    if DRY_RUN:
        print(f"  [revoca] roles con el código fuera de los holder: {stale_roles or 'ninguno'}")
    elif stale_roles:
        pull = db.roles.update_many(
            {"permissions": BOOKINGS_CODE, "role_name": {"$nin": list(BOOKINGS_HOLDER_ROLES)}},
            {"$pull": {"permissions": BOOKINGS_CODE}, "$set": {"updated_at": utc_now()}},
        )
        print(f"  [revoca] matched={pull.matched_count} modified={pull.modified_count} roles: {stale_roles}")

    # 3. Navegación — "Mis Reservas" pasa a su permiso propio + permission_id
    nav = db.navigation.find_one({"href": BOOKINGS_NAV_HREF})
    if nav is None:
        print(f"  [nav] ⚠ No existe ítem {BOOKINGS_NAV_HREF!r} en la colección navigation")
    else:
        current_req = nav.get("required_permission")
        perm_doc = db.permissions.find_one({"permission_code": BOOKINGS_CODE})
        if DRY_RUN:
            print(
                f"  [nav] {BOOKINGS_NAV_HREF!r}: required_permission "
                f"{current_req!r} → {BOOKINGS_CODE!r}"
                f"{' + refrescaría permission_id' if perm_doc else ' (⚠ sin perm_doc para permission_id)'}"
            )
        else:
            set_fields = {"required_permission": BOOKINGS_CODE, "updated_at": utc_now()}
            if perm_doc and perm_doc.get("_id"):
                set_fields["permission_id"] = perm_doc["_id"]
            db.navigation.update_one(
                {"href": BOOKINGS_NAV_HREF},
                {"$set": set_fields},
            )
            print(f"  [nav] {BOOKINGS_NAV_HREF!r} actualizado: required_permission={BOOKINGS_CODE!r}")

    client.close()
    if DRY_RUN:
        print("Nada modificado (--dry-run).")


if __name__ == "__main__":
    main()
