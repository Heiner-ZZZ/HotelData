"""Update Mi Portal navigation permission and clean up hr.read role assignments."""

from __future__ import annotations

import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from config.settings import get_settings
from pymongo import MongoClient


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    # 1. Require hr.read for the "Mi Portal" navigation item.
    nav_result = db.navigation.update_one(
        {"href": "/management/hr/my-portal"},
        {"$set": {"required_permission": "hr.read", "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)}},
    )
    print(f"Navigation 'Mi Portal' matched={nav_result.matched_count}, modified={nav_result.modified_count}")

    # 2. Remove hr.read from every role except the canonical employee role.
    role_result = db.roles.update_many(
        {"role_name": {"$ne": "maintenance"}},
        {"$pull": {"permissions": "hr.read"}},
    )
    print(f"Roles modified: {role_result.modified_count}")

    remaining = [r["role_name"] for r in db.roles.find({"permissions": "hr.read"}, {"role_name": 1})]
    print(f"Roles that still have hr.read: {remaining}")

    client.close()


if __name__ == "__main__":
    main()
