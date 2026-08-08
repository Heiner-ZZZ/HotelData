"""Check the current state of assigned_hotels in users and employees collections."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def main():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri)
    db = client[mongo_database]

    from bson import ObjectId

    # 1. Employees with user_id
    employees = list(
        db.employees.find(
            {"user_id": {"$ne": None, "$exists": True}},
            {"full_name": 1, "prop_id": 1, "user_id": 1},
        )
    )
    print("=" * 60)
    print(f"EMPLEADOS CON USER_ID: {len(employees)}")
    for emp in employees:
        uid = emp.get("user_id")
        try:
            uid_oid = uid if isinstance(uid, ObjectId) else ObjectId(uid)
            user = db.users.find_one(
                {"_id": uid_oid},
                {"username": 1, "assigned_hotels": 1},
            )
        except Exception:
            user = None
        if user:
            ah = user.get("assigned_hotels", [])
            print(f"  {emp['full_name']:30s} prop_id={emp.get('prop_id')}  →  user={user.get('username')}  assigned_hotels={ah}")
        else:
            print(f"  {emp['full_name']:30s} prop_id={emp.get('prop_id')}  →  USER NOT FOUND (id={uid})")

    # 2. All users with assigned_hotels
    print()
    print("USUARIOS CON assigned_hotels (exist):")
    users = list(
        db.users.find(
            {"assigned_hotels": {"$exists": True}},
            {"username": 1, "assigned_hotels": 1, "primary_role": 1},
        )
    )
    print(f"  Total: {len(users)}")
    for u in users:
        print(f"  {u.get('username','?'):25s} role={u.get('primary_role','?'):20s} assigned={u.get('assigned_hotels', [])}")

    client.close()


if __name__ == "__main__":
    main()
