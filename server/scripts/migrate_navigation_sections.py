"""Add ``section`` and ``is_section_header`` fields to navigation items.

Groups related items under collapsible sub-sections in the frontend sidebar.
Run this after deploying the new frontend sidebar that supports sub-sections.

Usage:
  docker compose -f infra/docker-compose.yml exec -T server python scripts/migrate_navigation_sections.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from dotenv import load_dotenv
from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# ── Section definitions: (href_prefix, section_name, is_section_header) ──
SECTION_MAPPINGS: list[tuple[str, str, bool]] = [
    # ── CRS (Central Reservation System) ──
    ("/management/availability", "CRS", False),
    ("/management/rates", "CRS", False),
    ("/management/check-ins", "CRS", False),
    ("/management/stay-inbox", "CRS", False),
    ("/management/check-outs", "CRS", False),
    ("/management/guests", "CRS", False),
    ("/management/policies", "CRS", False),
    # ── PMS (Property Management System) ──
    ("/management/properties", "PMS", False),
    ("/management/rooms", "PMS", False),
    ("/management/amenities", "PMS", False),
    ("/management/recepcion", "PMS", False),
    ("/management/reviews", "PMS", False),
    ("/management/audit-log", "PMS", False),
    ("/management/profile", "PMS", False),
    ("/management/lost-and-found", "PMS", False),
    ("/management/expenses", "PMS", False),
    # ── Housekeeping ──
    ("/management/housekeeping/maintenance", "Housekeeping", False),
    ("/management/housekeeping/charges", "Housekeeping", False),
    # ── RRHH ──
    ("/management/hr/my-portal", "RRHH", False),
    ("/management/hr/directory", "RRHH", False),
    ("/management/hr/onboarding", "RRHH", False),
    ("/management/hr/shifts", "RRHH", False),
    # ── Revenue ──
    ("/management/reports", "Revenue", False),
    # ── Billing ──
    ("/management/billing/invoices", "Billing", False),
]

# ── Section headers: (exact href, section_name, is_section_header) ──
SECTION_HEADERS: list[tuple[str, str, bool]] = [
    # ── CRS & PMS ──
    ("/management/reservations", "CRS", True),
    ("/management", "PMS", True),
    # ── Housekeeping, RRHH, Revenue, Billing ──
    ("/management/housekeeping", "Housekeeping", True),
    ("/management/hr", "RRHH", True),
    ("/management/revenue", "Revenue", True),
    ("/management/billing", "Billing", True),
]


def main() -> None:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27018")
    mongo_database = os.getenv("MONGO_DATABASE", "hoteldata_hub")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[mongo_database]

    updated = 0
    tagged = 0

    # Tag section headers (needs both section + is_section_header for frontend grouping)
    for href, section_name, is_header in SECTION_HEADERS:
        result = db.navigation.update_one(
            {"href": href},
            {"$set": {"section": section_name, "is_section_header": is_header}},
        )
        if result.modified_count:
            tagged += 1
            print(f"  ✓ Header: {href} → section='{section_name}'")

    # Tag section children
    for prefix, section_name, is_header in SECTION_MAPPINGS:
        result = db.navigation.update_one(
            {"href": {"$regex": f"^{prefix}"}},
            {"$set": {"section": section_name, "is_section_header": is_header}},
        )
        if result.modified_count:
            updated += 1
            print(f"  ✓ {prefix} → section='{section_name}'")

    # Ensure all items have section=None if not set (clean state)
    db.navigation.update_many(
        {"section": {"$exists": False}},
        {"$set": {"section": None}},
    )
    db.navigation.update_many(
        {"is_section_header": {"$exists": False}},
        {"$set": {"is_section_header": False}},
    )

    total = db.navigation.count_documents({})
    with_section = db.navigation.count_documents({"section": {"$ne": None}})
    headers = db.navigation.count_documents({"is_section_header": True})

    print(f"\n  Total: {total} | With section: {with_section} | Headers: {headers}")
    print(f"  Headers tagged: {tagged} | Children tagged: {updated}")
    client.close()


if __name__ == "__main__":
    main()
