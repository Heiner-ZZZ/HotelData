"""Add the ``lost-found.*`` permission resource + the Lost & Found nav item.

Contexto: el ítem de navegación "Lost & Found" (/management/lost-and-found)
exigía ``lost-found.read``, pero ese código no existía en la colección
``permissions`` — por eso aparecía **Oculto** en el editor de roles de
super_admin y no era otorgable. Además el API de lost & found exigía
``housekeeping.*`` (desalineado con la navegación). Este script:

1. Hace upsert de los 5 códigos ``lost-found.*`` en ``permissions`` (idempotente).
2. Con ``$addToSet`` (NUNCA $set — no pisa permisos personalizados en la UI)
   agrega lost-found.* a los roles que ya accedían vía housekeeping.*
   (paridad exacta read/update; el API acepta lost-found.* o housekeeping.*):
   - housekeeping: read/update
   - maintenance: read/update
3. Hace upsert del ítem de navegación Lost & Found (mantiene ``lost-found.read``).

Replica la entrada del ``PERMISSION_CATALOG`` / ``NAVIGATION_CATALOG`` de
``scripts/init_security_model_ga03.py`` (mantener en sync).

Run: python scripts/add_lost_found_permissions.py [--dry-run]
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

LOST_FOUND_PERMISSIONS = [
    ("lost-found.manage", "Administrar objetos perdidos — acceso total"),
    ("lost-found.create", "Registrar objeto perdido/encontrado"),
    ("lost-found.read", "Ver registros de lost & found"),
    ("lost-found.update", "Editar registros de lost & found"),
    ("lost-found.delete", "Eliminar registros de lost & found"),
]

# Roles que ya accedían al módulo vía housekeeping.* → migrar a lost-found.*
# PARIDAD EXACTA: se otorga solo lo que el rol ya tenía vía housekeeping.*
# (housekeeping: read/update · maintenance: read/update). El API acepta ambos
# códigos (require_any_permission) para no romper roles hotel-scoped ni
# personalizados durante la transición.
ROLE_LOST_FOUND: dict[str, list[str]] = {
    "housekeeping": ["lost-found.read", "lost-found.update"],
    "maintenance": ["lost-found.read", "lost-found.update"],
}

NAV_ITEM = {
    "href": "/management/lost-and-found",
    "label": "Lost & Found",
    "icon": "search",
    "required_permission": "lost-found.read",
    "section": "Housekeeping",
    "is_system": True,
    "sort_order": 304,
}

DRY_RUN = "--dry-run" in sys.argv


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[settings.mongo_database]
    print(f"DB: {db.name} ({'DRY-RUN' if DRY_RUN else 'aplicando'})")

    # 1. Permisos
    created = updated = 0
    for code, description in LOST_FOUND_PERMISSIONS:
        if DRY_RUN:
            exists = db.permissions.count_documents({"permission_code": code})
            print(f"  [permiso {'ya existe' if exists else 'faltaría'}] {code}")
            continue
        result = db.permissions.update_one(
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
    if not DRY_RUN:
        print(f"  permisos: {created} nuevos, {updated} actualizados")

    # 2. Roles — convergencia a la lista exacta de lost-found.* sin pisar el resto
    for role_name, codes in ROLE_LOST_FOUND.items():
        if DRY_RUN:
            role = db.roles.find_one({"role_name": role_name}, {"permissions": 1})
            current = set(role.get("permissions", [])) if role else set()
            missing = [c for c in codes if c not in current]
            extra = sorted(c for c in current if c.startswith("lost-found.") and c not in codes)
            print(f"  [rol {role_name}] agregaría: {missing} · quitaría: {extra}")
            continue
        # Primero quitar lost-found.* que no correspondan (paridad exacta), luego otorgar.
        pull = db.roles.update_one(
            {"role_name": role_name, "permissions": {"$elemMatch": {"$regex": "^lost-found\\."}}},
            {"$pull": {"permissions": {"$regex": "^lost-found\\."}}},
        )
        grant = db.roles.update_one(
            {"role_name": role_name},
            {"$addToSet": {"permissions": {"$each": codes}}, "$set": {"updated_at": utc_now()}},
        )
        print(f"  [rol {role_name}] pull={pull.modified_count} grant={grant.modified_count}")

    # 3. Navegación
    if DRY_RUN:
        exists = db.navigation.count_documents({"href": NAV_ITEM["href"]})
        print(f"  [nav] Lost & Found {'ya existe' if exists else 'faltaría'}")
    else:
        result = db.navigation.update_one(
            {"href": NAV_ITEM["href"]},
            {
                "$set": {**NAV_ITEM, "updated_at": utc_now()},
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        print(f"  [nav] matched={result.matched_count}, upserted={result.upserted_id is not None}")

    client.close()
    if DRY_RUN:
        print("Nada modificado (--dry-run).")


if __name__ == "__main__":
    main()
