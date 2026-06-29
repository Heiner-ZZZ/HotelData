"""Guest Folio — cuenta del huésped durante la estancia.

El folio es la cuenta viva que acumula todos los cargos (habitación, spa,
minibar, parking, lavandería, etc.) y descuentos durante la estancia del
huésped. Se crea en el check-in y se cierra en el check-out después de
generar la factura y procesar el pago.

Flujo:
  Check-in  → create_folio()          → posting inicial: habitación
  Durante   → post_to_folio()         → cada cargo adicional
  Check-out → Folio → Pago → Factura → close_folio()
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database

FOLIO_COLLECTION = "guest_folios"

# ── Helpers ──


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_folio_number() -> str:
    """Generate a sequential folio number: FL-YYYYMM-XXXX."""
    db = get_database()
    prefix = f"FL-{_now().strftime('%Y%m')}-"
    last = db[FOLIO_COLLECTION].find_one(
        {"folio_number": {"$regex": f"^{prefix}"}},
        sort=[("folio_number", -1)],
        projection={"folio_number": 1},
    )
    if last and last.get("folio_number"):
        try:
            seq = int(last["folio_number"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _find_booking(booking_id: str) -> dict | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        try:
            booking = db.booking_orders.find_one({"_id": ObjectId(booking_id)})
        except Exception:
            pass
    return booking


def _enrich_folio(doc: dict) -> dict:
    """Convert _id to id and format datetimes."""
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "closed_at"):
        if doc.get(f):
            if isinstance(doc[f], datetime):
                doc[f] = doc[f].isoformat()
    # Convert posting ObjectIds to strings
    for p in doc.get("postings", []):
        if isinstance(p.get("posting_id"), ObjectId):
            p["posting_id"] = str(p["posting_id"])
    return doc


# ── Core Operations ──


def create_folio(booking_id: str) -> dict | None:
    """Create a new folio for a booking at check-in.

    Automatically posts the initial room charge from the booking.
    Returns the folio dict, or None if booking not found.
    """
    booking = _find_booking(booking_id)
    if not booking:
        return None

    db = get_database()

    # Check if folio already exists
    existing = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    if existing:
        return _enrich_folio(existing)

    # Resolve room label
    assigned_rooms: list[str] = booking.get("assigned_rooms") or []
    room_label = ""
    if assigned_rooms:
        room_doc = db.hotel_rooms.find_one(
            {"hotel_room_id": assigned_rooms[0]},
            {"_id": 0, "room_label": 1, "room_number": 1},
        )
        if room_doc:
            room_label = room_doc.get("room_label", "") or room_doc.get("room_number", "")

    # Resolve hotel label
    prop_id = int(booking.get("prop_id", 0))
    hotel_label = ""
    if prop_id:
        ctx = db.hotel_booking_context.find_one(
            {"prop_id": prop_id}, {"_id": 0, "hotel_label": 1}
        )
        if ctx:
            hotel_label = ctx.get("hotel_label", "")

    # Calculate room charge from booking total_price
    total_price = float(booking.get("total_price", 0) or 0)
    total_nights = int(booking.get("total_nights", 1))
    room_rate = round(total_price / total_nights, 2) if total_nights > 0 else 0

    folio_number = _generate_folio_number()
    now = _now()

    # Initial posting: room charge
    initial_posting = {
        "posting_id": ObjectId(),
        "type": "room",
        "category": "Habitación",
        "concept": f"{booking.get('room_type_name', 'Habitación')} — {total_nights} noche(s)",
        "amount": total_price,
        "quantity": total_nights,
        "unit_price": room_rate,
        "reference_id": booking.get("booking_id", ""),
        "reference_type": "booking",
        "posted_at": now,
    }

    doc = {
        "folio_number": folio_number,
        "booking_id": booking.get("booking_id") or booking_id,
        "prop_id": prop_id,
        "guest_name": booking.get("guest_name", ""),
        "guest_email": booking.get("guest_email", ""),
        "room_label": room_label,
        "hotel_label": hotel_label,
        "check_in_date": booking.get("check_in_date", ""),
        "check_out_date": booking.get("check_out_date", ""),
        "status": "open",
        "total_room": total_price,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": total_price,
        "postings": [initial_posting],
        "posting_count": 1,
        "created_at": now,
        "closed_at": None,
        "closed_by": None,
        "invoice_id": None,
    }

    db[FOLIO_COLLECTION].insert_one(doc)
    return _enrich_folio(doc)


def get_folio(booking_id: str) -> dict | None:
    """Get the active folio for a booking by booking_id."""
    db = get_database()
    doc = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    return _enrich_folio(doc) if doc else None


def get_folio_by_id(folio_id: str) -> dict | None:
    """Get a folio by its ObjectId."""
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(folio_id)
    except (InvalidId, Exception):
        return None
    db = get_database()
    doc = db[FOLIO_COLLECTION].find_one({"_id": doc_id})
    return _enrich_folio(doc) if doc else None


def post_to_folio(
    booking_id: str,
    *,
    posting_type: str = "charge",
    category: str = "Otros",
    concept: str = "",
    amount: float = 0.0,
    quantity: int = 1,
    unit_price: float | None = None,
    reference_id: str = "",
    reference_type: str = "additional_charge",
) -> dict | None:
    """Post a transaction to the folio.

    Supports types: charge, discount, payment, adjustment.
    Automatically recalculates total_charges, total_discounts,
    total_payments, and total_due on the folio.

    Returns the updated folio, or None if not found.
    """
    db = get_database()

    amount = round(amount, 2)
    if unit_price is None:
        unit_price = round(amount / max(quantity, 1), 2)

    now = _now()
    posting = {
        "posting_id": ObjectId(),
        "type": posting_type,
        "category": category,
        "concept": concept,
        "amount": amount,
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "reference_id": reference_id,
        "reference_type": reference_type,
        "posted_at": now,
    }

    # Build the atomic update
    inc_fields: dict[str, float] = {}
    if posting_type == "charge":
        inc_fields["total_charges"] = amount
    elif posting_type == "discount":
        # Discounts are negative amounts
        inc_fields["total_discounts"] = abs(amount)
    elif posting_type == "payment":
        inc_fields["total_payments"] = amount
    elif posting_type == "adjustment":
        # Adjustments can be positive or negative
        if amount >= 0:
            inc_fields["total_charges"] = amount
        else:
            inc_fields["total_discounts"] = abs(amount)

    # Calculate new total_due: room + charges - discounts - payments
    folio = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    if not folio:
        return None

    new_total_due = (
        folio.get("total_room", 0)
        + folio.get("total_charges", 0) + inc_fields.get("total_charges", 0)
        - folio.get("total_discounts", 0) - inc_fields.get("total_discounts", 0)
        - folio.get("total_payments", 0) - inc_fields.get("total_payments", 0)
    )
    new_total_due = round(max(new_total_due, 0), 2)

    result = db[FOLIO_COLLECTION].find_one_and_update(
        {"booking_id": booking_id},
        {
            "$push": {"postings": posting},
            "$inc": {**inc_fields, "posting_count": 1},
            "$set": {"total_due": new_total_due, "updated_at": now},
        },
        return_document=ReturnDocument.AFTER,
    )
    return _enrich_folio(result) if result else None


def close_folio(
    booking_id: str,
    invoice_id: str | None = None,
    closed_by: str = "system",
) -> dict | None:
    """Close a folio at check-out after invoice and payment are settled.

    Sets status=closed, records the invoice_id, and stores the closing
    timestamp and user.
    """
    db = get_database()
    now = _now()

    result = db[FOLIO_COLLECTION].find_one_and_update(
        {"booking_id": booking_id, "status": "open"},
        {
            "$set": {
                "status": "closed",
                "closed_at": now,
                "closed_by": closed_by,
                "invoice_id": invoice_id,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _enrich_folio(result) if result else None


def list_folios(
    prop_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List folios with optional filters by property and status.

    Returns paginated results ordered by created_at descending.
    """
    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status:
        query["status"] = status

    total = db[FOLIO_COLLECTION].count_documents(query)
    cursor = (
        db[FOLIO_COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_folio(doc) for doc in cursor]

    import math
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


# ── Folio categories for charge posting ──

FOLIO_CATEGORIES = [
    {"id": "habitacion", "label": "Habitación", "icon": "bed"},
    {"id": "restaurante", "label": "Restaurante", "icon": "restaurant"},
    {"id": "bar", "label": "Bar", "icon": "local_bar"},
    {"id": "room_service", "label": "Room Service", "icon": "room_service"},
    {"id": "minibar", "label": "Minibar", "icon": "kitchen"},
    {"id": "spa", "label": "Spa", "icon": "spa"},
    {"id": "lavanderia", "label": "Lavandería", "icon": "local_laundry_service"},
    {"id": "parking", "label": "Parking", "icon": "local_parking"},
    {"id": "mascotas", "label": "Mascotas", "icon": "pets"},
    {"id": "llamadas", "label": "Llamadas", "icon": "phone"},
    {"id": "danos", "label": "Daños", "icon": "warning"},
    {"id": "late_checkout", "label": "Late Check-Out", "icon": "schedule"},
    {"id": "descuento", "label": "Descuento", "icon": "sell"},
    {"id": "otros", "label": "Otros", "icon": "more_horiz"},
]
