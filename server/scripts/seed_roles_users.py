"""Seed de usuarios demo (GA03) sobre el modelo de seguridad CANÓNICO.

ESTE SCRIPT YA NO ES UNA FUENTE DIVERGENTE de roles/permisos.

Antes (legacy): definía listas propias diminutas (``ROLES``/``PERMISSIONS``/
``ROLE_PERMISSIONS``) y las escribía con ``$set`` sobre
``roles.permissions``, pisando el catálogo canónico cada vez que se
re-ejecutaba después de ``init_security_model_ga03.py``.

Desde la migración (2026-08): importa ``BASE_ROLES``, ``PERMISSION_CATALOG``
y ``ROLE_PERMISSION_CODES`` (y las funciones de upsert) desde
``init_security_model_ga03.py`` — la fuente única de verdad. Su ÚNICO aporte
propio son los ``USERS`` demo.

Consecuencia práctica: correr este script es CONVERGENTE con el canónico.
Si el init canónico corrió antes, solo asegura usuarios demo; si no, deja
roles + permisos + mapeos en estado canónico de todos modos. Nunca degrada
permisos que el init canónico ya otorgó.
"""
from __future__ import annotations

import importlib.util
import os
from datetime import datetime, timezone
from pathlib import Path

from passlib.context import CryptContext
from pymongo import MongoClient

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Catálogo canónico: fuente única de verdad ──────────────────────────────
# Carga init_security_model_ga03.py por ruta (main() está guardado por
# `if __name__ == "__main__":`, así que importarlo no ejecuta side effects).
_INIT_PATH = Path(__file__).resolve().parent / "init_security_model_ga03.py"
_spec = importlib.util.spec_from_file_location(
    "init_security_model_ga03_canonical", _INIT_PATH
)
assert _spec and _spec.loader, f"no se pudo cargar {_INIT_PATH}"
_canonical = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_canonical)

BASE_ROLES = _canonical.BASE_ROLES
PERMISSION_CATALOG = _canonical.PERMISSION_CATALOG
ROLE_PERMISSION_CODES = _canonical.ROLE_PERMISSION_CODES
upsert_roles = _canonical.upsert_roles
upsert_permissions = _canonical.upsert_permissions
embed_role_permissions = _canonical.embed_role_permissions

USERS = [
    {"username": "admin", "email": "admin@hoteldata.local", "password": "Admin12345*", "primary_role": "super_admin", "display_name": "Administrador"},
    {"username": "gerente", "email": "gerente@hoteldata.local", "password": "HotelData2024*", "primary_role": "gerente_hotel", "display_name": "Gerente Hotel"},
    {"username": "operador", "email": "operador@hoteldata.local", "password": "HotelData2024*", "primary_role": "operador_datos", "display_name": "Operador Datos"},
    {"username": "cliente1", "email": "cliente1@test.com", "password": "Cliente2024*", "primary_role": "cliente", "display_name": "Cliente Demo"},
    {"username": "marketing", "email": "marketing@hoteldata.local", "password": "HotelData2024*", "primary_role": "marketing_hotelero", "display_name": "Marketing Hotelero"},
    {"username": "revenue", "email": "revenue@hoteldata.local", "password": "HotelData2024*", "primary_role": "revenue_manager", "display_name": "Revenue Manager"},
]


def seed(uri: str = "mongodb://localhost:27018", db_name: str = "hoteldata_hub"):
    client = MongoClient(uri)
    try:
        db = client[db_name]

        # Roles + permisos + mapeos: CANÓNICOS (convergentes, nunca divergentes).
        role_docs = upsert_roles(db["roles"])
        upsert_permissions(db["permissions"])
        embed_role_permissions(db["roles"], role_docs)
        print(
            f"Roles/permisos alineados al catálogo canónico "
            f"({len(BASE_ROLES)} roles, {len(PERMISSION_CATALOG)} códigos)"
        )

        # FK: role_name → roles._id so seeded users get ``primary_role_id``
        # (canonical user shape — see auth register + admin ownership).
        role_ids = {
            doc["role_name"]: doc["_id"]
            for doc in db.roles.find({}, {"role_name": 1, "_id": 1})
            if doc.get("role_name")
        }

        for u in USERS:
            now = datetime.now(timezone.utc)
            existing = db.users.find_one({"$or": [{"username": u["username"]}, {"email": u["email"]}]})
            primary_role_id = role_ids.get(u["primary_role"])
            if existing:
                update = {
                    "password_hash": ctx.hash(u["password"]),
                    "display_name": u["display_name"],
                    "primary_role": u["primary_role"],
                    # Fijar SIEMPRE (incluso None) para no dejar un FK stale de
                    # una corrida previa cuando el rol cambió/desapareció.
                    "primary_role_id": primary_role_id,
                    "is_active": True,
                    "email_verified": True,
                    "updated_at": now,
                }
                db.users.update_one({"_id": existing["_id"]}, {"$set": update})
                print(f"User {u['username']} updated OK")
            else:
                user_doc = {
                    "username": u["username"],
                    "email": u["email"],
                    "password_hash": ctx.hash(u["password"]),
                    "display_name": u["display_name"],
                    "primary_role": u["primary_role"],
                    "primary_role_id": primary_role_id,
                    "is_active": True,
                    "email_verified": True,
                    "failed_login_attempts": 0,
                    "locked_until": None,
                    "created_at": now,
                    "updated_at": now,
                }
                db.users.insert_one(user_doc)
                print(f"User {u['username']} ({u['primary_role']}) seeded OK")

        print("\nDone! Users created:")
        for u in USERS:
            print(f"  {u['username']:15s} / {u['password']:20s} -> {u['primary_role']}")
    finally:
        client.close()


if __name__ == "__main__":
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    db_name = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    seed(uri, db_name)
