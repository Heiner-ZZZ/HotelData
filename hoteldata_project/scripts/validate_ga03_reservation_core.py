from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.modules.reservations.service import (
    build_reservation_input,
    cancel_booking,
    cleanup_test_booking,
    create_booking,
    get_booking_detail,
)


def main() -> None:
    payload = build_reservation_input(
        {
            "prop_id": 1,
            "guest_name": "GA03 Test Guest",
            "guest_email": "ga03.test@example.local",
            "check_in_date": "2026-06-10",
            "check_out_date": "2026-06-12",
            "adults": 2,
            "children": 0,
            "rooms": 1,
            "comment": "Temporary validation booking",
            "created_by": "validate_ga03_reservation_core",
        },
        source="validation_script",
        is_test=True,
    )
    created = create_booking(payload)
    booking_id = created["booking_id"]
    detail_before = get_booking_detail(booking_id)
    cancelled = cancel_booking(booking_id, reason="validation_cleanup", changed_by="validate_ga03_reservation_core")
    detail_after = get_booking_detail(booking_id)
    cleanup = cleanup_test_booking(booking_id)

    report = {
        "ok": True,
        "booking_id": booking_id,
        "created": created,
        "detail_before_cancel": {
            "status": detail_before["booking"]["status"] if detail_before else None,
            "history_count": len(detail_before["history"]) if detail_before else 0,
        },
        "cancelled": cancelled,
        "detail_after_cancel": {
            "status": detail_after["booking"]["status"] if detail_after else None,
            "history_count": len(detail_after["history"]) if detail_after else 0,
        },
        "cleanup": cleanup,
    }
    print(json.dumps(report, indent=2, ensure_ascii=True, default=str))


if __name__ == "__main__":
    main()
