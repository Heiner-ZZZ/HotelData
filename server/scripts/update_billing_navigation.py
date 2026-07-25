"""Update the Billing navigation section to remove redundancy and add Payments."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from config.settings import get_settings
from pymongo import MongoClient


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    # Remove the redundant "Facturas" item that duplicates the Facturación header.
    delete_result = db.navigation.delete_one({"href": "/management/billing/invoices"})
    print(f"Deleted redundant 'Facturas' item: {delete_result.deleted_count}")

    # Upsert the "Pagos" item under the Billing section.
    upsert_result = db.navigation.update_one(
        {"href": "/management/billing/payments"},
        {
            "$set": {
                "label": "Pagos",
                "icon": "payments",
                "required_permission": "payments.read",
                "section": "Billing",
                "sort_order": 504,
                "is_system": True,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {
                "created_at": utc_now(),
            },
        },
        upsert=True,
    )
    print(f"Upserted 'Pagos' item: matched={upsert_result.matched_count}, upserted={upsert_result.upserted_id is not None}")

    # Ensure the "Facturación" header still exists.
    header_result = db.navigation.update_one(
        {"href": "/management/billing"},
        {
            "$set": {
                "label": "Facturación",
                "icon": "receipt",
                "required_permission": "billing.read",
                "section": "Billing",
                "is_section_header": True,
                "sort_order": 503,
                "is_system": True,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {
                "created_at": utc_now(),
            },
        },
        upsert=True,
    )
    print(f"Ensured 'Facturación' header: matched={header_result.matched_count}, upserted={header_result.upserted_id is not None}")

    client.close()


if __name__ == "__main__":
    main()
