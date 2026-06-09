from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

try:
    from passlib.context import CryptContext
except ImportError as exc:
    raise SystemExit(
        "Falta dependencia passlib[bcrypt]. Instala requirements.txt antes de ejecutar este script."
    ) from exc


SECURITY_COLLECTIONS = [
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_sessions",
    "user_activity_logs",
]

BASE_ROLES = [
    ("super_admin", "Super administrador", "Acceso total para inicializacion y gobierno del sistema."),
    ("admin_sistema", "Administrador del sistema", "Administra configuracion operativa de la plataforma."),
    ("operador_datos", "Operador de datos", "Ejecuta y monitorea tareas de datos y ETL."),
    ("auditor_datos", "Auditor de datos", "Consulta auditoria, calidad y trazabilidad."),
    ("hotel_partner", "Hotel partner", "Gestiona informacion operativa de propiedades asociadas."),
    ("gerente_hotel", "Gerente de hotel", "Consulta rendimiento y operacion de propiedades."),
    ("revenue_manager", "Revenue manager", "Analiza tarifas, promociones e ingresos."),
    ("marketing_hotelero", "Marketing hotelero", "Consulta promocion y rendimiento comercial."),
    ("cliente", "Cliente", "Usuario final planificado para busqueda y reservas."),
]

BASE_PERMISSIONS = [
    ("dashboard.read", "Leer dashboards"),
    ("crud.read", "Leer CRUD analitico"),
    ("crud.write", "Escribir CRUD analitico"),
    ("etl.execute", "Ejecutar ETL"),
    ("etl.read", "Leer estado ETL"),
    ("audit.read", "Leer auditoria"),
    ("users.manage", "Administrar usuarios"),
    ("hotels.manage", "Administrar hoteles"),
    ("reservations.manage", "Administrar reservas"),
    ("revenue.read", "Leer revenue"),
    ("revenue.manage", "Administrar revenue"),
]

ROLE_PERMISSION_CODES = {
    "super_admin": [code for code, _ in BASE_PERMISSIONS],
    "admin_sistema": [
        "dashboard.read",
        "crud.read",
        "crud.write",
        "etl.execute",
        "etl.read",
        "audit.read",
        "users.manage",
        "hotels.manage",
        "reservations.manage",
        "revenue.read",
        "revenue.manage",
    ],
    "operador_datos": ["dashboard.read", "etl.execute", "etl.read", "audit.read"],
    "auditor_datos": ["dashboard.read", "etl.read", "audit.read"],
    "hotel_partner": ["dashboard.read", "hotels.manage", "reservations.manage", "revenue.read"],
    "gerente_hotel": ["dashboard.read", "hotels.manage", "reservations.manage", "revenue.read"],
    "revenue_manager": ["dashboard.read", "revenue.read", "revenue.manage"],
    "marketing_hotelero": ["dashboard.read", "revenue.read"],
    "cliente": ["dashboard.read"],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[mongo_database]


def create_indexes(collections: dict[str, Collection]) -> None:
    collections["users"].create_index("email", unique=True)
    collections["users"].create_index("username", unique=True)
    collections["roles"].create_index("role_name", unique=True)
    collections["permissions"].create_index("permission_code", unique=True)
    collections["role_permissions"].create_index([("role_id", 1), ("permission_id", 1)], unique=True)
    collections["user_sessions"].create_index("session_token", unique=True, sparse=True)
    collections["user_sessions"].create_index("user_id")
    collections["user_activity_logs"].create_index("event_key", unique=True, sparse=True)
    collections["user_activity_logs"].create_index([("created_at", -1)])


def upsert_roles(roles: Collection) -> dict[str, Any]:
    role_docs: dict[str, Any] = {}
    for role_name, display_name, description in BASE_ROLES:
        roles.update_one(
            {"role_name": role_name},
            {
                "$set": {
                    "role_name": role_name,
                    "display_name": display_name,
                    "description": description,
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        role_docs[role_name] = roles.find_one({"role_name": role_name})
    return role_docs


def upsert_permissions(permissions: Collection) -> dict[str, Any]:
    permission_docs: dict[str, Any] = {}
    for permission_code, description in BASE_PERMISSIONS:
        permissions.update_one(
            {"permission_code": permission_code},
            {
                "$set": {
                    "permission_code": permission_code,
                    "description": description,
                    "is_system": True,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
        permission_docs[permission_code] = permissions.find_one({"permission_code": permission_code})
    return permission_docs


def upsert_role_permissions(
    role_permissions: Collection,
    role_docs: dict[str, Any],
    permission_docs: dict[str, Any],
) -> int:
    upserted = 0
    for role_name, permission_codes in ROLE_PERMISSION_CODES.items():
        role = role_docs[role_name]
        for permission_code in permission_codes:
            permission = permission_docs[permission_code]
            result = role_permissions.update_one(
                {"role_id": role["_id"], "permission_id": permission["_id"]},
                {
                    "$set": {
                        "role_name": role_name,
                        "permission_code": permission_code,
                        "updated_at": utc_now(),
                    },
                    "$setOnInsert": {"created_at": utc_now()},
                },
                upsert=True,
            )
            if result.upserted_id is not None:
                upserted += 1
    return upserted


def ensure_superadmin(users: Collection, role_docs: dict[str, Any]) -> dict[str, Any]:
    password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    super_admin_role = role_docs["super_admin"]
    existing_user = users.find_one({"$or": [{"username": "superadmin"}, {"email": "admin@hoteldata.local"}]})
    if existing_user:
        return {"created": False, "user_id": str(existing_user["_id"])}

    password_hash = password_context.hash("Admin12345*")
    result = users.insert_one(
        {
            "username": "superadmin",
            "email": "admin@hoteldata.local",
            "password_hash": password_hash,
            "temporary_password": True,
            "must_change_password": True,
            "is_active": True,
            "primary_role": "super_admin",
            "role_ids": [super_admin_role["_id"]],
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "created_by": "scripts/init_security_model_ga03.py",
        }
    )
    return {"created": True, "user_id": str(result.inserted_id)}


def register_activity(user_activity_logs: Collection, superadmin_result: dict[str, Any]) -> None:
    user_activity_logs.update_one(
        {"event_key": "ga03_security_model_initialized"},
        {
            "$set": {
                "event_key": "ga03_security_model_initialized",
                "action": "security_model.initialized",
                "module": "security",
                "details": {
                    "script": "scripts/init_security_model_ga03.py",
                    "superadmin_created": superadmin_result["created"],
                    "collections": SECURITY_COLLECTIONS,
                },
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )


def collection_counts(collections: dict[str, Collection]) -> dict[str, int]:
    return {name: collection.count_documents({}) for name, collection in collections.items()}


def main() -> None:
    db = get_database()
    collections = {name: db[name] for name in SECURITY_COLLECTIONS}
    create_indexes(collections)

    role_docs = upsert_roles(collections["roles"])
    permission_docs = upsert_permissions(collections["permissions"])
    role_permission_upserts = upsert_role_permissions(collections["role_permissions"], role_docs, permission_docs)
    superadmin_result = ensure_superadmin(collections["users"], role_docs)
    register_activity(collections["user_activity_logs"], superadmin_result)

    result = {
        "ok": True,
        "database": db.name,
        "created_or_verified_collections": SECURITY_COLLECTIONS,
        "roles_configured": len(BASE_ROLES),
        "permissions_configured": len(BASE_PERMISSIONS),
        "role_permission_upserts": role_permission_upserts,
        "superadmin": superadmin_result,
        "counts": collection_counts(collections),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
