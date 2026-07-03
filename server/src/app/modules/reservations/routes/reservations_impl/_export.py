"""Reservations CSV export logic."""

from __future__ import annotations

import csv
import io
from typing import Any

from src.database.connection import get_database


def export_reservations_csv(
    status_filter: str | None = None,
    prop_id: int | None = None,
) -> tuple[io.StringIO, str]:
    """Generate a CSV export of reservations with optional filters.

    Returns (output_buffer, raw_date_string).
    """
    db = get_database()
    filters: dict[str, Any] = {}
    if status_filter:
        filters["status"] = status_filter
    if prop_id:
        filters["prop_id"] = prop_id
    bookings = list(db.booking_orders.find(filters, {"_id": 0}).sort([("created_at", -1)]))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Booking ID", "Prop ID", "Status", "Guest Name", "Guest Email", "Guest Phone",
        "Check-in", "Check-out", "Adults", "Children", "Rooms",
        "Total Price", "Currency", "Total Nights", "Booking Source", "Created At", "Comment",
    ])
    for b in bookings:
        writer.writerow([
            b.get(k, "") for k in (
                "booking_id", "prop_id", "status", "guest_name", "guest_email",
                "guest_phone", "check_in_date", "check_out_date", "adults", "children", "rooms",
                "total_price", "currency", "total_nights", "booking_source", "created_at", "comment",
            )
        ])

    output.seek(0)
    raw_date = str(bookings[0].get("created_at", "export"))[:10] if bookings else "export"
    return output, raw_date
