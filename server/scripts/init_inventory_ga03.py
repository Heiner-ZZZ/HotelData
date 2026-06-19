from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from src.app.modules.partner.services import ensure_inventory_collections
from src.database.connection import get_database


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    summary = ensure_inventory_collections()
    db = get_database()
    counts = {
        "room_types": db.room_types.count_documents({}),
        "hotel_rooms": db.hotel_rooms.count_documents({}),
        "room_inventory_calendar": db.room_inventory_calendar.count_documents({}),
        "room_availability_blocks": db.room_availability_blocks.count_documents({}),
        "blackout_dates": db.blackout_dates.count_documents({}),
    }
    print(
        json.dumps(
            {
                "database": db.name,
                "created_collections": summary["collections"],
                "indexes_verified": summary["indexes"],
                "counts": counts,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
