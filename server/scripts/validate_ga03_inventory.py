from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from src.app.modules.partner.services import (
    create_blackout_block,
    create_room_type,
    ensure_inventory_collections,
    partner_hotel_inventory,
    partner_hotel_rooms,
    save_inventory_entry,
)
from src.database.connection import get_database


TEST_PROP_ID = 1
TEST_ROOM_NAME = "GA03 Test Suite"
TEST_ROOM_TYPE_ID = "RT-1-ga03-test-suite"


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    ensure_inventory_collections()
    db = get_database()

    before = {
        "room_types": db.room_types.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_rooms": db.hotel_rooms.count_documents({"prop_id": TEST_PROP_ID}),
        "room_inventory_calendar": db.room_inventory_calendar.count_documents({"prop_id": TEST_PROP_ID}),
        "room_availability_blocks": db.room_availability_blocks.count_documents({"prop_id": TEST_PROP_ID}),
        "blackout_dates": db.blackout_dates.count_documents({"prop_id": TEST_PROP_ID}),
    }

    create_room_type(
        TEST_PROP_ID,
        name=TEST_ROOM_NAME,
        description="Habitación creada para validación GA03",
        max_adults=2,
        max_children=1,
        base_capacity=2,
        is_active=True,
    )
    save_inventory_entry(
        TEST_PROP_ID,
        room_type_id=TEST_ROOM_TYPE_ID,
        date="2026-06-15",
        total_rooms=10,
        available_rooms=8,
        blocked_rooms=2,
    )
    create_blackout_block(
        TEST_PROP_ID,
        room_type_id=TEST_ROOM_TYPE_ID,
        start_date="2026-06-20",
        end_date="2026-06-22",
        reason="Mantenimiento preventivo",
        blocked_rooms=4,
    )

    rooms_detail = partner_hotel_rooms(TEST_PROP_ID)
    inventory_detail = partner_hotel_inventory(TEST_PROP_ID)

    db.room_inventory_calendar.delete_many({"prop_id": TEST_PROP_ID, "room_type_id": TEST_ROOM_TYPE_ID, "date": "2026-06-15"})
    db.room_availability_blocks.delete_many(
        {"prop_id": TEST_PROP_ID, "room_type_id": TEST_ROOM_TYPE_ID, "start_date": "2026-06-20", "end_date": "2026-06-22"}
    )
    db.blackout_dates.delete_many(
        {"prop_id": TEST_PROP_ID, "room_type_id": TEST_ROOM_TYPE_ID, "start_date": "2026-06-20", "end_date": "2026-06-22"}
    )
    db.hotel_rooms.delete_many({"prop_id": TEST_PROP_ID, "room_type_id": TEST_ROOM_TYPE_ID})
    db.room_types.delete_many({"prop_id": TEST_PROP_ID, "room_type_id": TEST_ROOM_TYPE_ID})

    after = {
        "room_types": db.room_types.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_rooms": db.hotel_rooms.count_documents({"prop_id": TEST_PROP_ID}),
        "room_inventory_calendar": db.room_inventory_calendar.count_documents({"prop_id": TEST_PROP_ID}),
        "room_availability_blocks": db.room_availability_blocks.count_documents({"prop_id": TEST_PROP_ID}),
        "blackout_dates": db.blackout_dates.count_documents({"prop_id": TEST_PROP_ID}),
    }

    report = {
        "ok": bool(rooms_detail and inventory_detail),
        "prop_id": TEST_PROP_ID,
        "before": before,
        "after_save": {
            "room_type_created": any(item["room_type_id"] == TEST_ROOM_TYPE_ID for item in (rooms_detail or {}).get("room_types", [])),
            "inventory_registered": any(item["room_type_id"] == TEST_ROOM_TYPE_ID for item in (inventory_detail or {}).get("inventory_items", [])),
            "blackout_registered": any(item["room_type_id"] == TEST_ROOM_TYPE_ID for item in (inventory_detail or {}).get("blackout_items", [])),
            "room_type_count_visible": len((rooms_detail or {}).get("room_types", [])),
        },
        "after_cleanup": after,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
