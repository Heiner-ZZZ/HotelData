"""Fulfillment checklists for a booking's special requests and amenities.

Each selected special request / amenity starts as ``pending`` when the
booking is created. During the active stay, reception/housekeeping can flip
each item to ``fulfilled`` (and back). The statuses live on the booking
document as:

- ``special_request_fulfillment: [{"label", "status", "updated_at", "fulfilled_at"}]``
- ``amenity_fulfillment: [{"label", "status", "updated_at", "fulfilled_at"}]``

``fulfilled_at`` records when the item was last marked fulfilled (``None``
while pending), giving both checklists a fulfillment date.

Legacy bookings (created before the fields existed) normalize every item to
``pending``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.database.connection import get_database

VALID_STATUSES = ("pending", "fulfilled")

# Booking document fields: source labels → fulfillment storage.
FULFILLMENT_FIELDS = {
    "special_request": ("special_requests", "special_request_fulfillment"),
    "amenity": ("selected_amenities", "amenity_fulfillment"),
}


def _normalize_fulfillment(
    labels: list[str],
    stored: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize stored fulfillment entries against the booking's labels.

    Every label present on the booking gets an entry; stored statuses win,
    anything else defaults to ``pending``. Stored ``fulfilled_at`` is kept
    only while the status is ``fulfilled``.
    """
    by_label: dict[str, dict[str, Any]] = {}
    for item in stored or []:
        if not isinstance(item, dict):
            continue
        by_label[str(item.get("label") or "").strip()] = item
    result: list[dict[str, Any]] = []
    for label in labels:
        if not label:
            continue
        item = by_label.get(label) or {}
        status = item.get("status") if item.get("status") in VALID_STATUSES else "pending"
        fulfilled_at = item.get("fulfilled_at") if status == "fulfilled" else None
        result.append({
            "label": label,
            "status": status,
            "fulfilled_at": fulfilled_at,
        })
    return result


def _labels_from(booking: dict[str, Any], field: str) -> list[str]:
    return [str(s).strip() for s in (booking.get(field) or []) if str(s).strip()]


def get_special_request_fulfillment(booking: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the stored fulfillment against the booking's request labels."""
    return _normalize_fulfillment(
        _labels_from(booking, "special_requests"),
        booking.get("special_request_fulfillment") or [],
    )


def get_amenity_fulfillment(booking: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the stored fulfillment against the booking's amenity labels."""
    return _normalize_fulfillment(
        _labels_from(booking, "selected_amenities"),
        booking.get("amenity_fulfillment") or [],
    )


def _update_fulfillment(booking_id: str, kind: str, label: str, status: str) -> list[dict[str, Any]]:
    """Set an item's fulfillment status on the booking (generic).

    ``kind`` must be ``"special_request"`` or ``"amenity"``. Raises
    ``ValueError`` when the booking doesn't exist, the label isn't one of the
    booking's items for that kind, or the status is invalid. Returns the
    normalized fulfillment list after the update.
    """
    if kind not in FULFILLMENT_FIELDS:
        raise ValueError("Tipo de checklist inválido.")
    source_field, storage_field = FULFILLMENT_FIELDS[kind]

    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 1, source_field: 1, storage_field: 1},
    )
    if booking is None:
        raise ValueError("Reserva no encontrada.")

    labels = _labels_from(booking, source_field)
    if label not in labels:
        raise ValueError(f"La petición '{label}' no pertenece a esta reserva.")

    status = status.strip()
    if status not in VALID_STATUSES:
        raise ValueError("Estado inválido. Usa 'pending' o 'fulfilled'.")

    now = datetime.now(timezone.utc).isoformat()
    stored = [item for item in (booking.get(storage_field) or []) if not isinstance(item, dict) or item.get("label") != label]
    stored.append({
        "label": label,
        "status": status,
        "updated_at": now,
        "fulfilled_at": now if status == "fulfilled" else None,
    })
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {storage_field: stored}},
    )
    # Reload with the new state to normalize against the booking's labels.
    fresh = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, source_field: 1, storage_field: 1},
    )
    return _normalize_fulfillment(_labels_from(fresh, source_field), fresh.get(storage_field) or [])


def update_special_request_fulfillment(booking_id: str, label: str, status: str) -> list[dict[str, Any]]:
    """Set a special request's fulfillment status on the booking."""
    return _update_fulfillment(booking_id, "special_request", label, status)


def update_amenity_fulfillment(booking_id: str, label: str, status: str) -> list[dict[str, Any]]:
    """Set an amenity's fulfillment status on the booking."""
    return _update_fulfillment(booking_id, "amenity", label, status)
