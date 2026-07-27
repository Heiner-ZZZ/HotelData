"""Invoice CRUD operations."""

from __future__ import annotations

import logging
import secrets

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database

logger = logging.getLogger(__name__)
from src.app.core.resolvers import resolve_hotel_id
from src.app.core.state_machine import invoice_sm
from src.app.modules.billing.schemas import InvoiceCreate
from src.app.modules.billing.service.lifecycle._helpers import (
    _enrich_invoice,
    _enrich_payment,
    _find_booking,
    _generate_invoice_number,
    _now,
    _update_both,
    _write_both,
    FACT_INVOICES,
    INVOICES,
    PAYMENTS,
)


def _record_earnings(booking: dict, invoice_total: float) -> None:
    """Calculate and record platform commission earnings."""
    db = get_database()
    prop_id = booking.get("prop_id", 0)
    booking_id = booking.get("booking_id", "")

    commission_cfg = db.commission_rates.find_one({"prop_id": prop_id}, {"commission_pct": 1, "_id": 0})
    if commission_cfg:
        commission_pct = commission_cfg.get("commission_pct", 5.0)
    else:
        sys_config = db.system_config.find_one({"_id": "global"}, {"default_commission_pct": 1, "_id": 0})
        commission_pct = sys_config.get("default_commission_pct", 5.0) if sys_config else 5.0

    commission_amount = round(invoice_total * commission_pct / 100, 2)

    from src.app.modules.partner.services.hotel_products import record_platform_earnings
    record_platform_earnings(
        booking_id=booking_id,
        prop_id=prop_id,
        commission_pct=commission_pct,
        booking_total=invoice_total,
        commission_amount=commission_amount,
    )


def generate_invoice_for_booking(
    booking_id: str, total_price: float | None = None,
    currency: str = "USD", notes: str = "",
) -> dict | None:
    """Auto-generate an invoice for a booking when confirmed."""
    booking = _find_booking(booking_id)
    if not booking:
        return None

    price = total_price if total_price else booking.get("total_price")
    if not price:
        price = 0.0
    price = float(price)
    subtotal = round(price / 1.16, 2)
    taxes = round(price - subtotal, 2)

    payload = InvoiceCreate(
        booking_id=booking.get("booking_id") or booking_id,
        subtotal=subtotal,
        taxes=taxes,
        notes=notes or f"Factura generada automáticamente por confirmación de reserva {booking.get('booking_id', '')}",
    )
    return create_invoice(payload)


def create_invoice(payload: InvoiceCreate) -> dict | None:
    booking = _find_booking(payload.booking_id)
    if not booking:
        return None

    line_items = booking.get("line_items", [])
    extras_total = sum(float(item.get("total", 0)) for item in line_items)
    room_subtotal = round(payload.subtotal, 2)
    total_subtotal = round(room_subtotal + extras_total, 2)
    total = round(total_subtotal + payload.taxes, 2)

    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(booking.get("prop_id", 0)),
        "invoice_number": _generate_invoice_number(),
        "subtotal": total_subtotal,
        "room_subtotal": room_subtotal,
        "extras_total": extras_total,
        "line_items": line_items,
        "taxes": round(payload.taxes, 2),
        "total": total,
        "status": "issued",
        "notes": payload.notes or None,
        "issued_at": _now(),
        "paid_at": None,
    }
    _write_both(INVOICES, FACT_INVOICES, doc)

    # Generate double-entry ledger entries from this invoice
    try:
        from src.app.modules.expenses.service.ledger_hooks import generate_ledger_from_invoice
        generate_ledger_from_invoice(doc)
    except Exception:
        logger.exception("Failed to generate ledger entries for invoice %s", doc.get("invoice_number", ""))

    try:
        _record_earnings(booking, total)
    except Exception:
        logger.exception("Failed to record earnings for booking %s", payload.booking_id)

    doc["_id"] = doc.pop("_id", None)
    return _enrich_invoice(doc)


def list_invoices(
    booking_id: str | None = None,
    prop_id: int | None = None,
    status: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}

    if prop_id:
        query["prop_id"] = prop_id
    if booking_id:
        booking = _find_booking(booking_id)
        booking_str_id = booking.get("booking_id") if booking else booking_id
        query["booking_id"] = booking_str_id
    if status:
        query["status"] = status
    if date_from or date_to:
        issued_q: dict = {}
        if date_from:
            issued_q["$gte"] = date_from
        if date_to:
            issued_q["$lte"] = date_to + "T23:59:59"
        query["issued_at"] = issued_q

    total = db[INVOICES].count_documents(query)
    cursor = (
        db[INVOICES]
        .find(query)
        .sort("issued_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for doc in cursor:
        enriched = _enrich_invoice(doc)
        inv_id = enriched.get("id", "")
        booking_id_field = enriched.get("booking_id", "")
        pid = int(enriched.get("prop_id", 0))

        booking_doc = db.booking_orders.find_one(
            {"booking_id": booking_id_field},
            {"_id": 0, "guest_name": 1},
        )
        enriched["guest_name"] = (booking_doc or {}).get("guest_name", "") if booking_doc else ""

        if pid:
            hotel = db.dim_hotels.find_one(
                {"prop_id": pid},
                {"_id": 0, "display_name": 1, "hotel_name": 1},
            )
            enriched["hotel_label"] = (
                hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel #{pid}"
            ) if hotel else f"Hotel #{pid}"
        else:
            enriched["hotel_label"] = ""

        try:
            payments_cursor = db[PAYMENTS].find(
                {"invoice_id": ObjectId(inv_id), "status": "confirmed"},
                {"_id": 0, "amount": 1},
            )
            total_paid = round(sum(float(p.get("amount", 0)) for p in payments_cursor), 2)
        except Exception:
            logger.warning("Failed to fetch payments for invoice %s", inv_id)
            total_paid = 0.0
        enriched["total_paid_amount"] = total_paid
        enriched["total_pending_amount"] = round(max(enriched.get("total", 0) - total_paid, 0), 2)

        if q:
            q_lower = q.lower()
            matches = (
                q_lower in booking_id_field.lower()
                or q_lower in enriched.get("guest_name", "").lower()
                or q_lower in enriched.get("invoice_number", "").lower()
            )
            if not matches:
                continue

        items.append(enriched)

    if q:
        total = len(items)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_invoice_stats() -> dict:
    """Return counts and totals grouped by invoice status."""
    db = get_database()
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_amount": {"$sum": {"$ifNull": ["$total", 0]}},
            },
        },
        {"$sort": {"_id": 1}},
    ]
    results = list(db[INVOICES].aggregate(pipeline))
    stats = {
        "issued": {"count": 0, "total": 0.0},
        "paid": {"count": 0, "total": 0.0},
        "cancelled": {"count": 0, "total": 0.0},
        "refunded": {"count": 0, "total": 0.0},
    }
    for r in results:
        key = r["_id"]
        if key in stats:
            stats[key]["count"] = r["count"]
            stats[key]["total"] = round(r["total_amount"], 2)
    return stats


def get_invoice(invoice_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc = db[INVOICES].find_one({"_id": ObjectId(invoice_id)})
    except (InvalidId, Exception):
        return None
    if not doc:
        return None
    enriched = _enrich_invoice(doc)

    booking_id = enriched.get("booking_id", "")
    prop_id = int(enriched.get("prop_id", 0))

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "cedula": 1,
         "check_in_date": 1, "check_out_date": 1, "total_nights": 1,
         "rooms": 1, "room_type_id": 1, "assigned_rooms": 1,
         "check_in_time": 1, "check_out_time": 1},
    )
    if booking:
        enriched["guest_name"] = booking.get("guest_name", "")
        enriched["guest_email"] = booking.get("guest_email", "")
        enriched["guest_cedula"] = booking.get("cedula", "")
        enriched["check_in_date"] = booking.get("check_in_date", "")
        enriched["check_out_date"] = booking.get("check_out_date", "")
        enriched["check_in_time"] = booking.get("check_in_time") or ""
        enriched["check_out_time"] = booking.get("check_out_time") or ""
        enriched["total_nights"] = booking.get("total_nights", 1)
        enriched["rooms"] = booking.get("rooms", 1)
        room_type_id = booking.get("room_type_id", "")
        if room_type_id:
            rt = db.room_types.find_one(
                {"room_type_id": room_type_id, "prop_id": prop_id},
                {"_id": 0, "name": 1},
            )
            enriched["room_type_name"] = rt.get("name", room_type_id) if rt else room_type_id
        else:
            enriched["room_type_name"] = ""
        assigned_ids = booking.get("assigned_rooms") or []
        room_labels = []
        if assigned_ids:
            room_docs = list(
                db.hotel_rooms.find(
                    {"hotel_room_id": {"$in": assigned_ids}},
                    {"_id": 0, "room_label": 1},
                )
            )
            for r in room_docs:
                room_labels.append(r.get("room_label", ""))
        enriched["room_labels"] = room_labels

    if prop_id:
        hotel = db.dim_hotels.find_one(
            {"prop_id": prop_id},
            {"_id": 0, "display_name": 1, "hotel_name": 1},
        )
        enriched["hotel_label"] = (
            hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel #{prop_id}"
        ) if hotel else f"Hotel #{prop_id}"
    else:
        enriched["hotel_label"] = ""

    payments = list(
        db[PAYMENTS].find({"invoice_id": ObjectId(invoice_id)}).sort("paid_at", -1).limit(50)
    )
    enriched["payments"] = [_enrich_payment(p) for p in payments]

    total_paid = round(
        sum(float(p.get("amount", 0)) for p in payments if p.get("status") == "confirmed"), 2,
    )
    enriched["total_paid_amount"] = total_paid
    enriched["total_pending_amount"] = round(max(enriched.get("total", 0) - total_paid, 0), 2)

    enriched["folio_id"] = None
    enriched["folio_number"] = None
    try:
        folio = db.guest_folios.find_one(
            {"booking_id": booking_id},
            {"_id": 1, "folio_number": 1},
        )
        if folio:
            enriched["folio_id"] = str(folio["_id"])
            enriched["folio_number"] = folio.get("folio_number")
    except Exception:
        logger.exception("Failed to fetch folio for booking %s", booking_id)

    return enriched


def add_line_item(
    invoice_id: str, *, name: str, quantity: int = 1,
    unit_price: float = 0.0, category: str = "Otros",
) -> dict | None:
    """Add a line item to an issued invoice and recalculate totals."""
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None

    inv = db[INVOICES].find_one({"_id": doc_id, "status": "issued"})
    if not inv:
        return None

    total = round(unit_price * quantity, 2)
    item_id = secrets.token_hex(8)
    new_item = {
        "item_id": item_id,
        "type": "manual_charge",
        "name": name,
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "total": total,
        "category": category,
        "created_at": _now(),
    }

    existing_items = inv.get("line_items", []) or []
    combined = existing_items + [new_item]
    extras_total = round(sum(float(it.get("total", 0)) for it in combined), 2)
    room_subtotal = inv.get("room_subtotal", 0) or 0
    new_subtotal = round(room_subtotal + extras_total, 2)
    new_taxes = round(new_subtotal * 0.16, 2)
    new_total = round(new_subtotal + new_taxes, 2)

    update = {
        "$push": {"line_items": new_item},
        "$set": {
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "updated_at": _now(),
        },
    }
    result = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": "issued"},
        update,
        return_document=ReturnDocument.AFTER,
    )
    if result:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": {
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "line_items": combined,
            "updated_at": _now(),
        }})
    return _enrich_invoice(result) if result else None


def remove_line_item(invoice_id: str, item_id: str) -> dict | None:
    """Remove a line item from an issued invoice and recalculate totals."""
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None

    inv = db[INVOICES].find_one({"_id": doc_id, "status": "issued"})
    if not inv:
        return None

    existing_items = inv.get("line_items", []) or []
    target = next((it for it in existing_items if it.get("item_id") == item_id), None)
    if not target:
        return None
    if target.get("type") == "room":
        return None

    remaining = [it for it in existing_items if it.get("item_id") != item_id]
    extras_total = round(sum(float(it.get("total", 0)) for it in remaining if it.get("type") != "room"), 2)
    room_subtotal = inv.get("room_subtotal", 0) or 0
    new_subtotal = round(room_subtotal + extras_total, 2)
    new_taxes = round(new_subtotal * 0.16, 2)
    new_total = round(new_subtotal + new_taxes, 2)

    update = {
        "$set": {
            "line_items": remaining,
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "updated_at": _now(),
        },
    }
    result = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": "issued"},
        update,
        return_document=ReturnDocument.AFTER,
    )
    if result:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": {
            "line_items": remaining,
            "extras_total": extras_total,
            "subtotal": new_subtotal,
            "taxes": new_taxes,
            "total": new_total,
            "updated_at": _now(),
        }})
    return _enrich_invoice(result) if result else None


def cancel_invoice(invoice_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None

    inv = db[INVOICES].find_one({"_id": doc_id}, {"status": 1})
    if not inv:
        return None

    # Validate with central StateMachine
    try:
        invoice_sm.validate_transition(inv.get("status", ""), "cancelled")
    except ValueError:
        return None

    doc = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": inv["status"]},
        {"$set": {"status": "cancelled", "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": {"status": "cancelled", "updated_at": _now()}})

        # Generate reversal double-entry ledger entries
        try:
            from src.app.modules.expenses.service.ledger_hooks import generate_reversal_from_invoice
            generate_reversal_from_invoice(doc)
        except Exception:
            logger.exception("Failed to generate ledger reversal for invoice %s", invoice_id)

    return _enrich_invoice(doc) if doc else None


def update_invoice_additional_charges(
    booking_id: str, *, changed_by: str = "angular_api",
) -> dict | None:
    """Fetch all additional_charges for a booking, sum them, and update the invoice."""
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION

    db = get_database()

    charges = list(db[CHARGES_COLLECTION].find({"booking_id": booking_id}))
    charges_sum = round(sum(c.get("total", 0) or 0 for c in charges), 2)

    if not charges and not db[INVOICES].find_one({"booking_id": booking_id}):
        return None

    inv = db[INVOICES].find_one({"booking_id": booking_id})
    if not inv:
        return None

    inv_id = inv["_id"]

    charge_items = []
    for c in charges:
        charge_items.append({
            "type": "additional_charge",
            "charge_id": str(c.get("_id", "")),
            "concept": c.get("concept", ""),
            "amount": c.get("amount", 0),
            "quantity": c.get("quantity", 1),
            "total": c.get("total", 0),
            "created_at": c.get("created_at", ""),
        })

    existing_line_items = inv.get("line_items", []) or []
    existing_charge_ids = {
        item["charge_id"] for item in existing_line_items
        if isinstance(item, dict) and item.get("type") == "additional_charge" and item.get("charge_id")
    }
    new_items = [item for item in charge_items if item["charge_id"] not in existing_charge_ids]
    if not new_items:
        return _enrich_invoice(inv)

    combined_line_items = existing_line_items + new_items

    room_subtotal = inv.get("room_subtotal", 0) or 0
    existing_extras = inv.get("extras_total", 0) or 0
    new_extras = round(existing_extras + charges_sum, 2)
    new_subtotal = round(room_subtotal + new_extras, 2)
    new_taxes = round(new_subtotal * 0.16, 2)
    new_total = round(new_subtotal + new_taxes, 2)

    update_doc = {
        "extras_total": new_extras,
        "subtotal": new_subtotal,
        "taxes": new_taxes,
        "total": new_total,
        "line_items": combined_line_items,
        "additional_charges": [
            {
                "charge_id": str(c.get("_id", "")),
                "concept": c.get("concept", ""),
                "amount": c.get("amount", 0),
                "quantity": c.get("quantity", 1),
                "total": c.get("total", 0),
            }
            for c in charges
        ],
        "updated_at": _now(),
    }

    new_charges_sum = round(sum(item["total"] for item in new_items), 2)

    db[INVOICES].update_one({"_id": inv_id}, {"$set": update_doc})
    db[FACT_INVOICES].update_one({"_id": inv_id}, {"$set": update_doc})

    # $inc only the NEW charges — preserves product line-item charges already on the booking
    if new_charges_sum > 0:
        db.booking_orders.update_one(
            {"booking_id": booking_id},
            {"$inc": {"total_charges": new_charges_sum},
             "$set": {"updated_at": _now()}},
        )
    else:
        db.booking_orders.update_one(
            {"booking_id": booking_id},
            {"$set": {"updated_at": _now()}},
        )

    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "settled_charges",
        "changed_at": _now(),
        "reason": f"Consumo liquidado: {len(new_items)} cargo(s) por ${charges_sum:.2f}",
        "changed_by": changed_by,
        "is_test": False,
    })

    updated = db[INVOICES].find_one({"_id": inv_id})
    return _enrich_invoice(updated) if updated else None


def create_split_charges_invoice(
    booking_id: str, *, changed_by: str = "angular_api",
) -> dict | None:
    """Create a separate invoice for additional charges only (split by charge type)."""
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION

    db = get_database()

    charges = list(db[CHARGES_COLLECTION].find({"booking_id": booking_id}))
    if not charges:
        return None

    charges_sum = round(sum(c.get("total", 0) or 0 for c in charges), 2)

    booking = _find_booking(booking_id)
    if not booking:
        return None

    room_inv = db[INVOICES].find_one({"booking_id": booking_id, "split_type": {"$ne": "charges_only"}})
    room_inv_id = room_inv["_id"] if room_inv else None

    charge_items = []
    for c in charges:
        charge_items.append({
            "type": "additional_charge",
            "charge_id": str(c.get("_id", "")),
            "concept": c.get("concept", "") or c.get("item_name", ""),
            "amount": c.get("amount", 0),
            "quantity": c.get("quantity", 1),
            "total": c.get("total", 0),
            "created_at": c.get("created_at", ""),
        })

    extras_total = charges_sum
    subtotal = charges_sum
    taxes = round(subtotal * 0.16, 2)
    total = round(subtotal + taxes, 2)

    inv_doc = {
        "booking_id": booking.get("booking_id") or booking_id,
        "prop_id": booking.get("prop_id", 0),
        "hotel_id": resolve_hotel_id(booking.get("prop_id", 0)),
        "invoice_number": _generate_invoice_number(),
        "subtotal": subtotal,
        "room_subtotal": 0,
        "extras_total": extras_total,
        "line_items": charge_items,
        "taxes": taxes,
        "total": total,
        "status": "issued",
        "split_type": "charges_only",
        "parent_invoice_id": str(room_inv_id) if room_inv_id else None,
        "notes": f"Factura de consumos — {len(charges)} cargo(s) adicional(es) por ${charges_sum:.2f}",
        "additional_charges": [
            {
                "charge_id": str(c.get("_id", "")),
                "concept": c.get("concept", "") or c.get("item_name", ""),
                "amount": c.get("amount", 0),
                "quantity": c.get("quantity", 1),
                "total": c.get("total", 0),
            }
            for c in charges
        ],
        "issued_at": _now(),
        "paid_at": None,
    }
    _write_both(INVOICES, FACT_INVOICES, inv_doc)

    if room_inv_id:
        db[INVOICES].update_one(
            {"_id": room_inv_id},
            {"$set": {
                "split_type": "room_only",
                "split_charges_invoice_id": str(inv_doc.get("_id") or inv_doc.get("inserted_id", "")),
                "updated_at": _now(),
            }},
        )
        db[FACT_INVOICES].update_one(
            {"_id": room_inv_id},
            {"$set": {
                "split_type": "room_only",
                "split_charges_invoice_id": str(inv_doc.get("_id") or inv_doc.get("inserted_id", "")),
                "updated_at": _now(),
            }},
        )

    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$inc": {"total_charges": charges_sum},
         "$set": {"split_invoice": True, "updated_at": _now()}},
    )

    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "split_charges_invoice",
        "changed_at": _now(),
        "reason": f"Factura de consumos separada creada: {len(charges)} cargo(s) por ${charges_sum:.2f}",
        "changed_by": changed_by,
        "is_test": False,
    })

    updated = db[INVOICES].find_one({"invoice_number": inv_doc["invoice_number"]})
    return _enrich_invoice(updated) if updated else None
