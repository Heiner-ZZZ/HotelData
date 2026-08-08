"""Grant ``reviews.read`` to the roles that currently see the \"Reseñas\" menu.

Contexto: el ítem de navegación ``/management/reviews`` exigía
``properties.read`` — los roles ``hotel_partner``, ``gerente_hotel`` y
``recepcionista`` veían \"Reseñas\" por accidente de tener ``properties.read``,
no por tener acceso real a reseñas. Este script:

1. Cambia el ítem de navegación \"Reseñas\" a ``required_permission:
   reviews.read`` (idempotente: si ya es reviews.read no modifica nada).
2. Con ``$addToSet`` (NUNCA $set — no pisa personalizaciones de la UI)
   otorga ``reviews.read`` a los tres roles para que conserven la vista del
   menú tras el cambio del ítem.

Replica NAVIGATION_CATALOG / ROLE_PERMISSION_CODES de
``scripts/init_security_model_ga03.py`` (mantener en sync) y el map de
``scripts/sync_role_permissions.py``.

Run: python scripts/add_reviews_read_viewer_roles.py [--dry-run]
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

REVIEWS_NAV_HREF = "/management/reviews"
REVIEWS_NAV_REQUIRED = "reviews.read"

# Roles que hoy ven \"Reseñas\" vía properties.read — paridad de acceso.
REVIEW_VIEWER_ROLES = ("hotel_partner", "gerente_hotel", "recepcionista")

DRY_RUN = "--dry-run" in sys.argv


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongo_database]
    print(f"DB: {db.name} ({'DRY-RUN' if DRY_RUN else 'aplicando'})")

    # 1. Ítem de navegación "Reseñas" → reviews.read
    nav = db.navigation.find_one({"href": REVIEWS_NAV_HREF})
    if not nav:
        print(f"  ⚠  No existe el ítem de navegación {REVIEWS_NAV_HREF}")
    else:
        current = nav.get("required_permission")
        if DRY_RUN:
            print(f"  [nav Reseñas] required_permission={current!r} → {REVIEWS_NAV_REQUIRED!r}")
        elif current != REVIEWS_NAV_REQUIRED:
            db.navigation.update_one(
                {"href": REVIEWS_NAV_HREF},
                {"$set": {"required_permission": REVIEWS_NAV_REQUIRED, "updated_at": utc_now()}},
            )
            print(f"  [nav Reseñas] required_permission: {current!r} → {REVIEWS_NAV_REQUIRED!r}")
        else:
            print(f"  [nav Reseñas] ya exige {REVIEWS_NAV_REQUIRED!r} — sin cambios")

    # 2. Roles — $addToSet (aditivo, converge, no pisa personalizaciones)
    for role_name in REVIEW_VIEWER_ROLES:
        if DRY_RUN:
            role = db.roles.find_one({"role_name": role_name}, {"permissions": 1})
            current = set(role.get("permissions", [])) if role else set()
            missing = [c for c in (REVIEWS_NAV_REQUIRED,) if c not in current]
            print(f"  [rol {role_name}] agregaría: {missing}")
            continue
        grant = db.roles.update_one(
            {"role_name": role_name},
            {
                "$addToSet": {"permissions": REVIEWS_NAV_REQUIRED},
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
