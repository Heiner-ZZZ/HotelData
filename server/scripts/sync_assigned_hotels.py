"""Sync assigned_hotels from employees collection to users collection.

For every employee that has both a user_id and a prop_id, this script
ensures the corresponding user document has that prop_id in assigned_hotels.

Usage:
    docker compose -f infra/docker-compose.yml exec -T server python scripts/sync_assigned_hotels.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def get_database():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client[mongo_database]


def main() -> None:
    db = get_database()

    # Find all employees with both a user_id and a prop_id
    employees = list(
        db.employees.find(
            {"user_id": {"$ne": None, "$exists": True}, "prop_id": {"$ne": None, "$exists": True}},
            {"_id": 0, "user_id": 1, "prop_id": 1, "full_name": 1},
        )
    )

    print(f"🔍 Empleados con user_id y prop_id: {len(employees)}")

    updated_count = 0
    skipped_count = 0
    errors = []

    for emp in employees:
        user_id = emp.get("user_id", "").strip()
        prop_id = emp.get("prop_id")
        name = emp.get("full_name", "desconocido")

        if not user_id or prop_id is None:
            skipped_count += 1
            continue

        from bson import ObjectId

        try:
            # Check if user exists
            user = db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 1, "assigned_hotels": 1})
            if not user:
                print(f"  ⚠ Usuario no encontrado para {name} (user_id={user_id}), saltando.")
                skipped_count += 1
                continue

            current_assigned = user.get("assigned_hotels", [])
            if prop_id in current_assigned:
                # Already has it — skip
                skipped_count += 1
                continue

            # Add prop_id to assigned_hotels
            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$addToSet": {"assigned_hotels": prop_id},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )
            print(f"  ✅ {name:25s} → assigned_hotels +{prop_id} (era: {current_assigned})")
            updated_count += 1

        except Exception as exc:
            print(f"  ❌ Error con {name} (user_id={user_id}): {exc}")
            errors.append({"name": name, "user_id": user_id, "error": str(exc)})

    print(f"\n{'='*50}")
    print(f"📊 Resumen:")
    print(f"   Total empleados con user_id+prop_id: {len(employees)}")
    print(f"   ✅ Actualizados:  {updated_count}")
    print(f"   ⏭  Saltados (ya OK): {skipped_count}")
    print(f"   ❌ Errores:       {len(errors)}")

    if errors:
        for e in errors:
            print(f"     - {e['name']}: {e['error']}")

    return updated_count


if __name__ == "__main__":
    count = main()
    print(f"\n🎯 {count} usuario(s) actualizado(s).")
