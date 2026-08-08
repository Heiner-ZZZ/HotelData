"""Add the ``reviews.*`` permission resource to the security model.

Contexto: ``PATCH/DELETE /api/reviews/{id}`` exigen ``reviews.moderate``
(moderar y eliminar reseñas), pero ese código no existía en la colección
``permissions`` — ningún rol no-super_admin podía moderar (403 del backend),
aunque la UI mostrara el botón a ``marketing_hotelero``. El editor de roles
además exige ``reviews.read`` como dependencia de lectura para poder otorgar
``reviews.moderate`` (regla ``ensure_read_dependencies`` en ``role_update.py``),
por eso los dos códigos viajan juntos. Este script:

1. Hace upsert de los 2 códigos ``reviews.*`` en ``permissions`` (idempotente).
2. Con ``$addToSet`` (NUNCA $set — no pisa permisos personalizados de la UI)
   otorga ``reviews.read`` + ``reviews.moderate`` a ``marketing_hotelero``
   (el rol que modera reseñas según el docstring del API).
3. No toca navegación: el ítem \"Reseñas\" sigue exigiendo ``properties.read``.

Replica la entrada del ``PERMISSION_CATALOG`` / ``ROLE_PERMISSION_CODES`` de
``scripts/init_security_model_ga03.py`` (mantener en sync).

Run: python scripts/add_reviews_permissions.py [--dry-run]
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

REVIEWS_PERMISSIONS = [
    ("reviews.read", "Ver reseñas y su estado de moderación"),
    ("reviews.moderate", "Moderar y eliminar reseñas (aprobar/rechazar)"),
]

# Roles que reciben los códigos. $addToSet converge sin borrar nada: si en el
# futuro un rol añade reviews.* por la UI, re-correr este script lo conserva.
ROLE_REVIEWS: dict[str, list[str]] = {
    "marketing_hotelero": ["reviews.read", "reviews.moderate"],
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
    for code, description in REVIEWS_PERMISSIONS:
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

    # 2. Roles — $addToSet (aditivo, converge, no pisa personalizaciones)
    for role_name, codes in ROLE_REVIEWS.items():
        if DRY_RUN:
            role = db.roles.find_one({"role_name": role_name}, {"permissions": 1})
            current = set(role.get("permissions", [])) if role else set()
            missing = [c for c in codes if c not in current]
            print(f"  [rol {role_name}] agregaría: {missing}")
            continue
        grant = db.roles.update_one(
            {"role_name": role_name},
            {"$addToSet": {"permissions": {"$each": codes}}, "$set": {"updated_at": utc_now()}},
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
