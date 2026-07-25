"""Update HR menu permissions and managerial role access.

This script is idempotent: running it multiple times produces the same result.

Changes:
- Grants ``hr.manage`` to ``admin_sistema`` and ``gerente_hotel`` so they can
  perform onboarding, edit employees, and manage shifts.
- Updates the navigation catalog so that:
  - ``Mi Portal`` and the ``RRHH`` section header remain ``hr.read``
    (visible to all hotel staff with an employee profile).
  - ``Directorio RRHH`` and ``Turnos`` require ``hr.manage`` (only managers
    and admins see them).
  - ``Onboarding`` keeps ``hr.create``, which is covered by ``hr.manage``.
"""
from __future__ import annotations

import json
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


def main() -> dict:
    db = get_database()

    # 1. Grant hr.manage to managerial roles
    role_result = db.roles.update_many(
        {"role_name": {"$in": ["admin_sistema", "gerente_hotel"]}},
        {"$addToSet": {"permissions": "hr.manage"}},
    )

    # 2. Update navigation items
    nav_updates = [
        ("/management/hr/directory", "hr.manage"),
        ("/management/hr/shifts", "hr.manage"),
    ]
    nav_modified = 0
    for href, permission in nav_updates:
        result = db.navigation.update_one(
            {"href": href},
            {"$set": {"required_permission": permission, "updated_at": datetime.now(timezone.utc)}},
        )
        if result.matched_count:
            nav_modified += result.modified_count

    return {
        "roles_matched": role_result.matched_count,
        "roles_modified": role_result.modified_count,
        "navigation_items_updated": nav_modified,
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2, ensure_ascii=False))
