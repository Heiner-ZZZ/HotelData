from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

try:
    from passlib.context import CryptContext
except ImportError as exc:
    raise SystemExit(
        "Falta dependencia passlib[bcrypt]. Instala requirements.txt antes de ejecutar este script."
    ) from exc


PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_USERS = [
    {
        "username": "superadmin",
        "email": "admin@hoteldata.local",
        "password": "Admin12345*",
        "role": "super_admin",
        "display_name": "Super Admin Demo",
        "suggested_routes": ["/admin/security", "/etl-status", "/ta02"],
    },
    {
        "username": "operador",
        "email": "operador@hoteldata.local",
        "password": "Operador123*",
        "role": "operador_datos",
        "display_name": "Operador Demo",
        "suggested_routes": ["/etl-status", "/analytics/reservations", "/ta02"],
    },
    {
        "username": "auditor",
        "email": "auditor@hoteldata.local",
        "password": "Auditor123*",
        "role": "auditor_datos",
        "display_name": "Auditor Demo",
        "suggested_routes": ["/admin/security", "/analytics/conversion", "/audit"],
    },
    {
        "username": "partner",
        "email": "partner@hoteldata.local",
        "password": "Partner123*",
        "role": "hotel_partner",
        "display_name": "Partner Demo",
        "suggested_routes": ["/partner/hotels", "/partner/hotels/1/content", "/partner/hotels/1/inventory"],
    },
    {
        "username": "gerente",
        "email": "gerente@hoteldata.local",
        "password": "Gerente123*",
        "role": "gerente_hotel",
        "display_name": "Gerente Hotel Demo",
        "suggested_routes": ["/partner/hotels/1/performance", "/analytics/revenue", "/hotels/search"],
    },
    {
        "username": "revenue",
        "email": "revenue@hoteldata.local",
        "password": "Revenue123*",
        "role": "revenue_manager",
        "display_name": "Revenue Demo",
        "suggested_routes": ["/revenue/rate-plans", "/revenue/promotions", "/analytics/revenue"],
    },
    {
        "username": "marketing",
        "email": "marketing@hoteldata.local",
        "password": "Marketing123*",
        "role": "marketing_hotelero",
        "display_name": "Marketing Demo",
        "suggested_routes": ["/revenue/promotions", "/analytics/promotions", "/hotels/compare"],
    },
    {
        "username": "cliente",
        "email": "cliente@hoteldata.local",
        "password": "Cliente123*",
        "role": "cliente",
        "display_name": "Cliente Demo",
        "suggested_routes": ["/hotels/search", "/hotels/compare", "/reservations/new"],
    },
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[mongo_database]


def resolve_role_map(db) -> dict[str, dict[str, Any]]:
    roles = {item["role_name"]: item for item in db.roles.find({}, {"_id": 1, "role_name": 1})}
    missing = [user["role"] for user in DEMO_USERS if user["role"] not in roles]
    if missing:
        raise SystemExit(f"Faltan roles en MongoDB: {sorted(set(missing))}. Ejecute primero init_security_model_ga03.py")
    return roles


def upsert_demo_user(db, role_map: dict[str, dict[str, Any]], user_data: dict[str, Any]) -> dict[str, Any]:
    role = role_map[user_data["role"]]
    now = utc_now()
    password_hash = PASSWORD_CONTEXT.hash(user_data["password"])
    existing = db.users.find_one(
        {
            "$or": [
                {"username": user_data["username"]},
                {"email": user_data["email"]},
            ]
        },
        {"_id": 1},
    )
    filter_doc = {"_id": existing["_id"]} if existing else {"email": user_data["email"]}
    update_result = db.users.update_one(
        filter_doc,
        {
            "$set": {
                "username": user_data["username"],
                "email": user_data["email"],
                "display_name": user_data["display_name"],
                "password_hash": password_hash,
                "temporary_password": True,
                "must_change_password": False,
                "is_active": True,
                "primary_role": user_data["role"],
                "role_ids": [role["_id"]],
                "updated_at": now,
                "updated_by": "scripts/create_demo_users_ga03.py",
            },
            "$setOnInsert": {
                "created_at": now,
                "created_by": "scripts/create_demo_users_ga03.py",
            },
        },
        upsert=True,
    )
    saved_user = db.users.find_one({"email": user_data["email"]}, {"_id": 1, "username": 1, "email": 1, "primary_role": 1})
    db.user_activity_logs.insert_one(
        {
            "user_id": saved_user["_id"] if saved_user else None,
            "username": user_data["username"],
            "email": user_data["email"],
            "action": "security.demo_user_upserted",
            "module": "security",
            "details": {
                "script": "scripts/create_demo_users_ga03.py",
                "role": user_data["role"],
                "suggested_routes": user_data["suggested_routes"],
                "created": update_result.upserted_id is not None,
            },
            "created_at": now,
        }
    )
    return {
        "username": user_data["username"],
        "email": user_data["email"],
        "role": user_data["role"],
        "created": update_result.upserted_id is not None,
    }


def main() -> None:
    db = get_database()
    role_map = resolve_role_map(db)
    results = [upsert_demo_user(db, role_map, user_data) for user_data in DEMO_USERS]
    counts = {
        "users": db.users.count_documents({}),
        "roles": db.roles.count_documents({}),
        "permissions": db.permissions.count_documents({}),
        "user_sessions": db.user_sessions.count_documents({}),
        "user_activity_logs": db.user_activity_logs.count_documents({}),
    }
    print(
        json.dumps(
            {
                "ok": True,
                "database": db.name,
                "demo_users_processed": results,
                "counts": counts,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
