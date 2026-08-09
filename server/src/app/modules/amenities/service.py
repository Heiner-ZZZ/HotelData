"""Guest-facing amenity catalog and request service with stock management."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.app.modules.partner.services._common import normalize_label
from src.app.modules.partner.services.content.amenities import (
    _amenity_unit_price,
    amenities_payload_for_prop,
)
from src.app.modules.partner.services.content.queries import content_page_for_prop
from src.database.connection import get_database

logger = logging.getLogger(__name__)

STOCK_COLLECTION = "amenity_stock"

# ── Stock management ──────────────────────────────────────────────


def _ensure_stock_indexes() -> None:
    db = get_database()
    existing = db[STOCK_COLLECTION].index_information()
    if "prop_amenity_room" not in existing:
        db[STOCK_COLLECTION].create_index(
            [("prop_id", 1), ("amenity_label", 1), ("room_type_id", 1)],
            name="prop_amenity_room",
            unique=True,
        )


def get_amenity_stock(
    prop_id: int,
    room_type_id: str = "",
) -> dict[str, int]:
    """Return a dict mapping amenity_label -> available_stock for a property.

    Results are scoped: if ``room_type_id`` is provided, returns only
    room-type-specific stock; otherwise returns hotel-wide stock
    (where room_type_id is empty).
    """
    db = get_database()
    query: dict[str, Any] = {"prop_id": prop_id}
    if room_type_id:
        query["room_type_id"] = room_type_id
    else:
        query["room_type_id"] = {"$in": ["", None]}

    records = db[STOCK_COLLECTION].find(query, {"_id": 0, "amenity_label": 1, "available_stock": 1})
    return {r["amenity_label"]: int(r.get("available_stock", 0)) for r in records}


def _check_amenity_availability(
    prop_id: int,
    room_type_id: str,
    amenity_label: str,
    quantity: int,
) -> tuple[bool, str]:
    """Check if an amenity has sufficient stock.

    Returns (available, reason) where reason is empty if available.
    First tries room-type-specific stock, then falls back to hotel-wide stock.
    """
    db = get_database()
    # Try room-type-specific first
    stock = db[STOCK_COLLECTION].find_one(
        {"prop_id": prop_id, "amenity_label": amenity_label, "room_type_id": room_type_id},
        {"_id": 0, "available_stock": 1},
    )
    if stock:
        avail = int(stock.get("available_stock", 0))
        if avail < quantity:
            return False, f"Solo hay {avail} disponible(s) de '{amenity_label}' para este tipo de habitación."
        return True, ""

    # Fall back to hotel-wide stock (room_type_id is empty)
    stock = db[STOCK_COLLECTION].find_one(
        {"prop_id": prop_id, "amenity_label": amenity_label, "room_type_id": {"$in": ["", None]}},
        {"_id": 0, "available_stock": 1},
    )
    if stock:
        avail = int(stock.get("available_stock", 0))
        if avail < quantity:
            return False, f"Solo hay {avail} disponible(s) de '{amenity_label}' en todo el hotel."
        return True, ""

    # No stock record — assume unlimited
    return True, ""


def _release_amenity(
    prop_id: int,
    room_type_id: str,
    amenity_label: str,
    quantity: int,
) -> bool:
    """Return a previously reserved unit to the same scoped stock bucket."""
    db = get_database()
    query = {
        "prop_id": prop_id,
        "amenity_label": amenity_label,
        "room_type_id": room_type_id,
    }
    result = db[STOCK_COLLECTION].update_one(
        query,
        {"$inc": {"available_stock": quantity}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if result.modified_count:
        return True
    result = db[STOCK_COLLECTION].update_one(
        {"prop_id": prop_id, "amenity_label": amenity_label, "room_type_id": {"$in": ["", None]}},
        {"$inc": {"available_stock": quantity}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    return bool(result.modified_count)


def _reserve_amenity(
    prop_id: int,
    room_type_id: str,
    amenity_label: str,
    quantity: int,
) -> bool:
    """Decrement available stock for an amenity.

    Tries room-type-specific first, then hotel-wide.
    Returns True if decremented, False if no stock record found (unlimited amenity).
    """
    db = get_database()
    result = db[STOCK_COLLECTION].update_one(
        {"prop_id": prop_id, "amenity_label": amenity_label, "room_type_id": room_type_id,
         "available_stock": {"$gte": quantity}},
        {"$inc": {"available_stock": -quantity}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if result.modified_count > 0:
        return True

    # Try hotel-wide
    result = db[STOCK_COLLECTION].update_one(
        {"prop_id": prop_id, "amenity_label": amenity_label, "room_type_id": {"$in": ["", None]},
         "available_stock": {"$gte": quantity}},
        {"$inc": {"available_stock": -quantity}, "$set": {"updated_at": datetime.now(timezone.utc)}},
    )
    if result.modified_count > 0:
        return True

    return False  # No stock record — unlimited or insufficient


# ── Stock CRUD for partners ───────────────────────────────────────

def set_amenity_stock(
    prop_id: int,
    amenity_label: str,
    *,
    total_stock: int,
    room_type_id: str = "",
) -> dict[str, Any]:
    """Create or update the stock level for an amenity."""
    _ensure_stock_indexes()
    db = get_database()
    clean_label = normalize_label(amenity_label)
    if not clean_label:
        raise ValueError("Debe indicar el nombre de la amenidad.")
    total = max(0, int(total_stock or 0))

    payload = {
        "prop_id": prop_id,
        "amenity_label": clean_label,
        "room_type_id": normalize_label(room_type_id),
        "total_stock": total,
        "available_stock": total,
        "updated_at": datetime.now(timezone.utc),
    }
    doc = db[STOCK_COLLECTION].find_one_and_update(
        {"prop_id": prop_id, "amenity_label": clean_label, "room_type_id": payload["room_type_id"]},
        {"$set": payload, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
        return_document=True,
        projection={"_id": 0},
    )
    return doc


def list_amenity_stock(
    prop_id: int | None = None,
    amenity_label: str | None = None,
) -> list[dict[str, Any]]:
    """List stock records with optional filters."""
    _ensure_stock_indexes()
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id is not None:
        query["prop_id"] = prop_id
    if amenity_label:
        query["amenity_label"] = amenity_label
    return list(db[STOCK_COLLECTION].find(query, {"_id": 0}).sort([("amenity_label", 1)]))


# ── Guest-facing endpoints logic ──────────────────────────────────

def get_guest_amenity_catalog(booking_id: str) -> dict[str, Any] | None:
    """Return the amenity catalog for the hotel linked to this booking.

    Includes available stock for each amenity.
    Returns None if the booking is not found.
    """
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "prop_id": 1, "guest_name": 1, "check_in_date": 1, "check_out_date": 1,
         "status": 1, "room_type_id": 1},
    )
    if not booking:
        return None

    prop_id = booking["prop_id"]
    room_type_id = booking.get("room_type_id", "")

    amenities_data = amenities_payload_for_prop(prop_id, room_type_id=room_type_id)

    # Enrich catalog items with available stock
    stock_map = get_amenity_stock(prop_id, room_type_id=room_type_id)
    # Also get hotel-wide stock for fallback display
    hotel_wide_stock = get_amenity_stock(prop_id) if room_type_id else {}

    catalog = amenities_data.get("catalog", [])
    for category in catalog:
        for item in category.get("items", []):
            label = item.get("label", "")
            stock = stock_map.get(label)
            if stock is None:
                stock = hotel_wide_stock.get(label)
            item["available_stock"] = stock  # None = unlimited

    # Resolve hotel_label from hotel dimension
    hotel_label = ""
    if prop_id:
        try:
            hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"_id": 0, "hotel_name": 1, "display_name": 1})
            if hotel:
                hotel_label = hotel.get("display_name") or hotel.get("hotel_name", "") or str(prop_id)
        except Exception:
            logger.exception("Failed to resolve hotel_label for prop_id=%s", prop_id)

    return {
        "booking": {
            "booking_id": booking_id,
            "guest_name": booking.get("guest_name", ""),
            "check_in": booking.get("check_in_date", ""),
            "check_out": booking.get("check_out_date", ""),
            "status": booking.get("status", ""),
            "hotel_label": hotel_label,
        },
        "catalog": catalog,
        "active_amenities": amenities_data.get("active_amenities", []),
    }


def request_amenities(
    booking_id: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Process a guest's amenity request with stock validation.

    For each item:
    1. Checks stock availability (if tracked)
    2. Reserves stock
    3. Creates additional charges for paid amenities

    If ANY item in the request has insufficient stock, the entire
    request is rejected with details about what's unavailable.

    Each item in ``items`` must have ``label`` (str) and ``quantity`` (int >= 1).
    """
    if not items:
        return {"ok": True, "charges_created": 0, "total": 0.0, "items": []}

    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "prop_id": 1, "guest_name": 1, "guest_email": 1, "room_type_id": 1},
    )
    if not booking:
        raise ValueError(f"Booking '{booking_id}' not found.")

    prop_id = booking["prop_id"]
    room_type_id = booking.get("room_type_id", "")

    # ── Pre-check aggregated stock for ALL items before processing ──
    # Duplicate lines are one reservation, not independent availability checks.
    requested: dict[str, int] = {}
    for req in items:
        label = normalize_label(req.get("label", ""))
        if label:
            requested[label] = requested.get(label, 0) + max(1, int(req.get("quantity", 1)))
    stock_errors: list[str] = []
    for label, qty in requested.items():
        ok, reason = _check_amenity_availability(prop_id, room_type_id, label, qty)
        if not ok:
            stock_errors.append(reason)

    if stock_errors:
        return {
            "ok": False,
            "charges_created": 0,
            "total": 0.0,
            "items": [],
            "stock_errors": stock_errors,
            "message": "No se pudo completar la solicitud. Algunos servicios no tienen stock suficiente.",
        }

    # ── Process items ──
    page = content_page_for_prop(prop_id)
    stored_prices: dict[str, float] = {
        k.lower(): float(v)
        for k, v in (page.get("amenity_prices") or {}).items()
    }

    from src.app.modules.housekeeping.schemas import AdditionalChargeCreate
    from src.app.modules.housekeeping.service.lifecycle.charges import (
        create_additional_charge,
    )

    created: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    total = 0.0

    for req in items:
        label = normalize_label(req.get("label", ""))
        qty = max(1, int(req.get("quantity", 1)))
        if not label:
            continue

        # Reserve stock atomically. A tracked stock bucket returning False is
        # a hard failure; only a missing bucket means unlimited service.
        try:
            has_room_bucket = db[STOCK_COLLECTION].find_one({
                "prop_id": prop_id, "amenity_label": label, "room_type_id": room_type_id,
            }, {"_id": 1})
            has_hotel_bucket = db[STOCK_COLLECTION].find_one({
                "prop_id": prop_id, "amenity_label": label, "room_type_id": {"$in": ["", None]},
            }, {"_id": 1})
            reserved = _reserve_amenity(prop_id, room_type_id, label, qty)
            if (has_room_bucket or has_hotel_bucket) and not reserved:
                failed.append({"label": label, "quantity": qty, "reason": "stock_reservation_failed"})
                continue
        except Exception:
            logger.exception("Failed to reserve stock for %s", label)
            failed.append({"label": label, "quantity": qty, "reason": "stock_reservation_failed"})
            continue

        unit_price = stored_prices.get(label.lower(), _amenity_unit_price(label))
        if unit_price <= 0:
            created.append({"label": label, "quantity": qty, "amount": 0.0, "free": True})
            continue

        try:
            charge_payload = AdditionalChargeCreate(
                booking_id=booking_id,
                prop_id=prop_id,
                concept=f"Amenidad solicitada: {label}",
                amount=unit_price,
                quantity=qty,
                note="Solicitado por huésped durante la estancia.",
            )
            charge_result = create_additional_charge(charge_payload)
            if charge_result and charge_result.get("posting_status") == "posted":
                line_total = round(unit_price * qty, 2)
                total += line_total
                created.append({
                    "label": label,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "amount": line_total,
                    "free": False,
                    "charge_id": charge_result.get("id"),
                })
            else:
                _release_amenity(prop_id, room_type_id, label, qty)
                failed.append({"label": label, "quantity": qty, "reason": "folio_posting_failed"})
        except Exception:
            _release_amenity(prop_id, room_type_id, label, qty)
            failed.append({"label": label, "quantity": qty, "reason": "charge_creation_failed"})
            logger.exception(
                "Failed to create charge for amenity %s on booking %s",
                label, booking_id
            )


    # The request contract is all-or-nothing. Compensate every item that was
    # already committed when a later item failed; otherwise the response says
    # failure while stock, charges, and folio postings remain partially sold.
    if failed:
        from src.app.modules.housekeeping.service.lifecycle.charges import delete_additional_charge
        for item in created:
            _release_amenity(prop_id, room_type_id, item["label"], item["quantity"])
            if item.get("charge_id"):
                delete_additional_charge(item["charge_id"])
        created = []
        total = 0.0

    # ── Notify staff about the amenity request ──
    if created:
        try:
            from src.app.modules.amenities.notifications import (
                notify_guest_amenity_request,
                notify_staff_amenity_request,
            )
            notify_staff_amenity_request(
                prop_id=prop_id,
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                items=created,
                total=round(total, 2),
            )
        except Exception:
            logger.exception(
                "Failed to send staff amenity-request notification for booking %s", booking_id
            )

        # ── Notify guest that their request was processed ──
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email:
                # Resolve hotel label for the email
                hotel_label = ""
                try:
                    hotel = db.dim_hotels.find_one(
                        {"prop_id": prop_id},
                        {"_id": 0, "display_name": 1, "hotel_name": 1},
                    )
                    if hotel:
                        hotel_label = hotel.get("display_name") or hotel.get("hotel_name", "") or str(prop_id)
                except Exception:
                    logger.exception("Failed to resolve hotel_label for guest notification prop_id=%s", prop_id)

                notify_guest_amenity_request(
                    guest_email=guest_email,
                    guest_name=booking.get("guest_name", "Huésped"),
                    booking_id=booking_id,
                    prop_id=prop_id,
                    items=created,
                    total=round(total, 2),
                    hotel_label=hotel_label or f"Hotel #{prop_id}",
                )
        except Exception:
            logger.exception(
                "Failed to send guest amenity-request confirmation for booking %s", booking_id
            )

    return {
        "ok": not failed,
        "charges_created": len([c for c in created if not c.get("free")]),
        "total": round(total, 2),
        "items": created,
        "failed_items": failed,
    }
