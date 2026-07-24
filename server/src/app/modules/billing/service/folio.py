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

from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from src.app.core.resolvers import resolve_hotel_id
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
    # Add expiry info
    doc["is_expired"] = _is_folio_expired(doc)
    doc["has_invoice"] = bool(doc.get("invoice_id"))
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

    # Resolve room label and hotel_room_id
    assigned_rooms: list[str] = booking.get("assigned_rooms") or []
    room_label = ""
    hotel_room_id = ""
    if assigned_rooms:
        room_doc = db.hotel_rooms.find_one(
            {"hotel_room_id": assigned_rooms[0]},
            {"_id": 0, "hotel_room_id": 1, "room_label": 1},
        )
        if room_doc:
            room_label = room_doc.get("room_label", "")
            hotel_room_id = room_doc.get("hotel_room_id", "")

    # Resolve hotel label
    prop_id = int(booking.get("prop_id", 0))
    hotel_label = ""
    if prop_id:
        ctx = db.dim_hotels.find_one(
            {"prop_id": prop_id}, {"_id": 0, "display_name": 1}
        )
        if ctx:
            hotel_label = ctx.get("display_name", "")

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
        "hotel_id": resolve_hotel_id(prop_id),
        "guest_name": booking.get("guest_name", ""),
        "guest_email": booking.get("guest_email", ""),
        "room_label": room_label,
        "hotel_room_id": hotel_room_id,
        "hotel_label": hotel_label,
        "check_in_date": booking.get("check_in_date", ""),
        "check_out_date": booking.get("check_out_date", ""),
        "check_in_time": booking.get("check_in_time", ""),
        "check_out_time": booking.get("check_out_time", ""),
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
    """Get the active folio for a booking by booking_id.

    Re-resolves hotel_label and check-in/out times from the booking
    for backward compatibility with folios created before these fields
    were stored.
    """
    db = get_database()
    doc = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    if not doc:
        return None

    updates: dict = {}

    # Re-resolve hotel_label if missing
    if not doc.get("hotel_label"):
        prop_id = int(doc.get("prop_id", 0))
        if prop_id:
            ctx = db.hotel_booking_context.find_one(
                {"prop_id": prop_id}, {"_id": 0, "hotel_label": 1}
            )
            if ctx and ctx.get("hotel_label"):
                updates["hotel_label"] = ctx["hotel_label"]

    # Fetch booking for times (if any field missing)
    if not doc.get("check_in_time") or not doc.get("check_out_time") or not doc.get("hotel_label"):
        booking = _find_booking(booking_id)
        if booking:
            if not doc.get("check_in_time") and booking.get("check_in_time"):
                updates["check_in_time"] = booking["check_in_time"]
            if not doc.get("check_out_time") and booking.get("check_out_time"):
                updates["check_out_time"] = booking["check_out_time"]

    if updates:
        db[FOLIO_COLLECTION].update_one({"booking_id": booking_id}, {"$set": updates})
        doc.update(updates)

    return _enrich_folio(doc)


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

    # Build atomic $inc fields — total_due is incremented atomically
    # alongside its component fields, eliminating the TOCTOU race.
    inc_fields: dict[str, float] = {}
    if posting_type == "charge":
        inc_fields["total_charges"] = amount
        inc_fields["total_due"] = amount
    elif posting_type == "discount":
        inc_fields["total_discounts"] = abs(amount)
        inc_fields["total_due"] = -abs(amount)
    elif posting_type == "payment":
        inc_fields["total_payments"] = amount
        inc_fields["total_due"] = -amount
    elif posting_type == "adjustment":
        # Adjustments can be positive or negative — total_due follows the sign
        if amount >= 0:
            inc_fields["total_charges"] = amount
        else:
            inc_fields["total_discounts"] = abs(amount)
        inc_fields["total_due"] = amount

    result = db[FOLIO_COLLECTION].find_one_and_update(
        {"booking_id": booking_id},
        {
            "$push": {"postings": posting},
            "$inc": {**inc_fields, "posting_count": 1},
            "$set": {"updated_at": now},
        },
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        return None

    # Floor total_due at 0 in the rare case $inc drove it negative
    if result.get("total_due", 0) < 0:
        db[FOLIO_COLLECTION].update_one(
            {"booking_id": booking_id},
            {"$set": {"total_due": 0}},
        )
        result["total_due"] = 0
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


def cleanup_expired_folios(prop_id: int | None = None) -> dict:
    """Close open folios whose check-out date has already passed.

    Returns count of newly-closed folios.
    """
    db = get_database()
    from src.app.core.timezone import local_today
    today = local_today()

    match: dict = {"status": "open"}
    if prop_id:
        match["prop_id"] = prop_id

    expired_ids: list[str] = []
    for doc in db[FOLIO_COLLECTION].find(match, {"booking_id": 1, "check_out_date": 1, "folio_number": 1}):
        co = str(doc.get("check_out_date", ""))[:10]
        if co and co < today:
            expired_ids.append(doc["booking_id"])

    closed = 0
    if expired_ids:
        result = db[FOLIO_COLLECTION].update_many(
            {"booking_id": {"$in": expired_ids}, "status": "open"},
            {"$set": {
                "status": "closed",
                "closed_at": _now(),
                "closed_by": "auto_cleanup_expired",
                "updated_at": _now(),
            }},
        )
        closed = result.modified_count

    return {"ok": True, "closed": closed, "prop_id": prop_id}


def _is_folio_expired(doc: dict) -> bool:
    """Check if a folio's check-out date has passed."""
    co = str(doc.get("check_out_date", ""))[:10]
    if not co:
        return False
    from src.app.core.timezone import local_today
    return co < local_today()


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
