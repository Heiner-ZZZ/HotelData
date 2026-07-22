from __future__ import annotations


from passlib.context import CryptContext
from pymongo import MongoClient

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLES = [
    "super_admin", "admin_sistema", "operador_datos", "auditor_datos",
    "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero",
    "cliente",
]

PERMISSIONS = [
    "users.manage", "dashboard.read", "crud.read", "crud.write",
    "etl.read", "etl.execute", "reservations.manage", "hotels.manage",
    "revenue.read", "revenue.manage", "audit.read",
]

ROLE_PERMISSIONS = {
    "super_admin": PERMISSIONS,
    "admin_sistema": ["users.manage", "dashboard.read", "etl.read", "audit.read"],
    "operador_datos": ["etl.read", "dashboard.read", "audit.read"],
    "auditor_datos": ["audit.read", "etl.read"],
    "hotel_partner": ["hotels.manage", "reservations.manage", "dashboard.read"],
    "gerente_hotel": ["hotels.manage", "reservations.manage", "revenue.read", "dashboard.read"],
    "revenue_manager": ["revenue.read", "revenue.manage", "dashboard.read"],
    "marketing_hotelero": ["hotels.manage", "revenue.read", "dashboard.read"],
    "cliente": [],
}

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
    db = client[db_name]

    for role_name in ROLES:
        db.roles.update_one(
            {"role_name": role_name},
            {"$set": {"role_name": role_name, "description": f"Rol {role_name}", "updated_at": None}},
            upsert=True,
        )
    print(f"Seeded {len(ROLES)} roles")

    for perm in PERMISSIONS:
        desc = perm.replace(".", " ").title()
        db.permissions.update_one(
            {"permission_code": perm},
            {"$set": {"permission_code": perm, "description": desc}},
            upsert=True,
        )
    print(f"Seeded {len(PERMISSIONS)} permissions")

    for role_name, perms in ROLE_PERMISSIONS.items():
        db.roles.update_one(
            {"role_name": role_name},
            {"$set": {"permissions": perms, "updated_at": None}},
            upsert=True,
        )
    print("Seeded role-permission mappings (embedded in roles)")

    for u in USERS:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        existing = db.users.find_one({"$or": [{"username": u["username"]}, {"email": u["email"]}]})
        if existing:
            db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "password_hash": ctx.hash(u["password"]),
                    "display_name": u["display_name"],
                    "primary_role": u["primary_role"],
                    "is_active": True,
                    "updated_at": now,
                }},
            )
            print(f"User {u['username']} updated OK")
        else:
            db.users.insert_one({
                "username": u["username"],
                "email": u["email"],
                "password_hash": ctx.hash(u["password"]),
                "display_name": u["display_name"],
                "primary_role": u["primary_role"],
                "is_active": True,
                "email_verified": True,
                "failed_login_attempts": 0,
                "locked_until": None,
                "created_at": now,
                "updated_at": now,
            })
            print(f"User {u['username']} ({u['primary_role']}) seeded OK")

    print("\nDone! Users created:")
    for u in USERS:
        print(f"  {u['username']:15s} / {u['password']:20s} -> {u['primary_role']}")


if __name__ == "__main__":
    import os
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    db_name = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    seed(uri, db_name)
