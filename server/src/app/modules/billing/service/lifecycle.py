from __future__ import annotations

import secrets
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument

from src.database.connection import get_database
from src.app.modules.billing.schemas import InvoiceCreate, PaymentCreate

INVOICES = "reservation_invoices"
PAYMENTS = "reservation_payments"
FACT_INVOICES = "fact_reservation_invoices"
FACT_PAYMENTS = "fact_reservation_payments"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write_both(collection: str, fact_collection: str, doc: dict) -> None:
    db = get_database()
    result = db[collection].insert_one(doc)
    fact_doc = {**doc, "operational_id": result.inserted_id, "_id": result.inserted_id}
    db[fact_collection].insert_one(fact_doc)


def _update_both(collection: str, fact_collection: str, doc_id: ObjectId, update: dict) -> None:
    db = get_database()
    db[collection].update_one({"_id": doc_id}, update)
    db[fact_collection].update_one({"_id": doc_id}, update)


def _generate_invoice_number() -> str:
    """Generate sequential invoice number: INV-YYYYMM-XXXX where XXXX is sequential per month."""
    db = get_database()
    prefix = f"INV-{_now().strftime('%Y%m')}-"
    # Find the highest sequence for this month
    last = db[INVOICES].find_one(
        {"invoice_number": {"$regex": f"^{prefix}"}},
        sort=[("invoice_number", -1)],
        projection={"invoice_number": 1},
    )
    if last and last.get("invoice_number"):
        try:
            seq = int(last["invoice_number"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


# --- Invoices ---

# --- Invoices ---

def _find_booking(booking_id: str) -> dict | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking:
        try:
            booking = db.booking_orders.find_one({"_id": ObjectId(booking_id)})
        except Exception:
            pass
    return booking


def generate_invoice_for_booking(booking_id: str, total_price: float | None = None, currency: str = "USD", notes: str = "") -> dict | None:
    """Auto-generate an invoice for a booking when confirmed.

    Calculates subtotal and taxes (IVA 16%) from the total_price.
    If total_price is None/0, attempts to look it up from the booking.
    """
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
        notes=notes or f"Factura generada automaticamente por confirmacion de reserva {booking.get('booking_id', '')}"
    )
    return create_invoice(payload)


def create_invoice(payload: InvoiceCreate) -> dict | None:
    db = get_database()
    booking = _find_booking(payload.booking_id)
    if not booking:
        return None

    # Include add-on products (line_items) from the booking
    line_items = booking.get("line_items", [])
    extras_total = sum(float(item.get("total", 0)) for item in line_items)
    room_subtotal = round(payload.subtotal, 2)
    total_subtotal = round(room_subtotal + extras_total, 2)
    total = round(total_subtotal + payload.taxes, 2)

    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
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

    # Record platform earnings (commission) based on global settings
    try:
        _record_earnings(booking, total)
    except Exception:
        pass

    doc["_id"] = doc.pop("_id", None)
    return _enrich_invoice(doc)


def _record_earnings(booking: dict, invoice_total: float) -> None:
    """Calculate and record platform commission earnings."""
    db = get_database()
    prop_id = booking.get("prop_id", 0)
    booking_id = booking.get("booking_id", "")

    # Get commission rate: check per-hotel override first, then global default
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


def list_invoices(
    booking_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}
    if booking_id:
        # Match either string booking_id or check if it matches the object id of booking
        booking = _find_booking(booking_id)
        booking_str_id = booking.get("booking_id") if booking else booking_id
        query["booking_id"] = booking_str_id
    if status:
        query["status"] = status
    total = db[INVOICES].count_documents(query)
    cursor = (
        db[INVOICES]
        .find(query)
        .sort("issued_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_invoice(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


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

    # ── Enrich with booking/guest/hotel data ──
    booking_id = enriched.get("booking_id", "")
    prop_id = int(enriched.get("prop_id", 0))

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "cedula": 1,
         "check_in_date": 1, "check_out_date": 1, "total_nights": 1,
         "rooms": 1, "room_type_id": 1, "assigned_rooms": 1},
    )
    if booking:
        enriched["guest_name"] = booking.get("guest_name", "")
        enriched["guest_email"] = booking.get("guest_email", "")
        enriched["guest_cedula"] = booking.get("cedula", "")
        enriched["check_in_date"] = booking.get("check_in_date", "")
        enriched["check_out_date"] = booking.get("check_out_date", "")
        enriched["total_nights"] = booking.get("total_nights", 1)
        enriched["rooms"] = booking.get("rooms", 1)
        # Resolve room type name
        room_type_id = booking.get("room_type_id", "")
        if room_type_id:
            rt = db.room_types.find_one(
                {"room_type_id": room_type_id, "prop_id": prop_id},
                {"_id": 0, "name": 1},
            )
            enriched["room_type_name"] = rt.get("name", room_type_id) if rt else room_type_id
        else:
            enriched["room_type_name"] = ""
        # Resolve assigned room labels
        assigned_ids = booking.get("assigned_rooms") or []
        room_labels = []
        if assigned_ids:
            room_docs = list(
                db.hotel_rooms.find(
                    {"hotel_room_id": {"$in": assigned_ids}},
                    {"_id": 0, "room_label": 1, "room_number": 1},
                )
            )
            for r in room_docs:
                room_labels.append(r.get("room_label", "") or r.get("room_number", ""))
        enriched["room_labels"] = room_labels

    # Hotel label
    if prop_id:
        ctx = db.hotel_booking_context.find_one({"prop_id": prop_id}, {"_id": 0, "hotel_label": 1})
        enriched["hotel_label"] = ctx.get("hotel_label", "") if ctx else f"Hotel #{prop_id}"
    else:
        enriched["hotel_label"] = ""

    # ── Fetch payments for this invoice ──
    payments = list(
        db[PAYMENTS].find({"invoice_id": ObjectId(invoice_id)}).sort("paid_at", -1).limit(50)
    )
    enriched["payments"] = [_enrich_payment(p) for p in payments]

    return enriched


def cancel_invoice(invoice_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(invoice_id)
    except (InvalidId, Exception):
        return None
    
    doc = db[INVOICES].find_one_and_update(
        {"_id": doc_id, "status": "issued"},
        {"$set": {"status": "cancelled", "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        _update_both(INVOICES, FACT_INVOICES, doc_id, {"$set": {"status": "cancelled", "updated_at": _now()}})
    return _enrich_invoice(doc) if doc else None


# --- Payments ---

def create_payment(payload: PaymentCreate) -> dict | None:
    db = get_database()
    booking = _find_booking(payload.booking_id)
    if not booking:
        return None
    invoice_id = None
    if payload.invoice_id:
        inv = db[INVOICES].find_one({"_id": ObjectId(payload.invoice_id)})
        if inv:
            invoice_id = ObjectId(payload.invoice_id)

    doc = {
        "booking_id": booking.get("booking_id") or payload.booking_id,
        "prop_id": booking.get("prop_id", 0),
        "invoice_id": invoice_id,
        "amount": round(payload.amount, 2),
        "method": payload.method,
        "status": "confirmed",
        "reference": f"PAY-{secrets.token_hex(6).upper()}",
        "paid_at": _now(),
    }
    _write_both(PAYMENTS, FACT_PAYMENTS, doc)

    if invoice_id:
        upd = {"$set": {"status": "paid", "paid_at": _now()}}
        _update_both(INVOICES, FACT_INVOICES, invoice_id, upd)

    doc["_id"] = doc.pop("_id", None)
    return _enrich_payment(doc)


def list_payments(
    booking_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    db = get_database()
    query: dict = {}
    if booking_id:
        booking = _find_booking(booking_id)
        booking_str_id = booking.get("booking_id") if booking else booking_id
        query["booking_id"] = booking_str_id
    total = db[PAYMENTS].count_documents(query)
    cursor = (
        db[PAYMENTS]
        .find(query)
        .sort("paid_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_payment(doc) for doc in cursor]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


def get_payment(payment_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        doc = db[PAYMENTS].find_one({"_id": ObjectId(payment_id)})
    except (InvalidId, Exception):
        return None
    return _enrich_payment(doc) if doc else None


def refund_payment(payment_id: str) -> dict | None:
    db = get_database()
    try:
        from bson.errors import InvalidId
        pay_id = ObjectId(payment_id)
    except (InvalidId, Exception):
        return None
        
    pay = db[PAYMENTS].find_one_and_update(
        {"_id": pay_id, "status": "confirmed"},
        {"$set": {"status": "refunded", "updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if pay:
        _update_both(PAYMENTS, FACT_PAYMENTS, pay_id, {"$set": {"status": "refunded", "updated_at": _now()}})
        if pay.get("invoice_id"):
            inv_id = pay["invoice_id"]
            upd = {"$set": {"status": "refunded", "updated_at": _now()}}
            _update_both(INVOICES, FACT_INVOICES, inv_id, upd)
    return _enrich_payment(pay) if pay else None


# --- Enrichment ---

def _fmt(val):
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def _enrich_invoice(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["booking_id"] = str(doc.get("booking_id", ""))
    for f in ("issued_at", "paid_at"):
        doc[f] = _fmt(doc.get(f))
    return doc


def update_invoice_additional_charges(booking_id: str, *, changed_by: str = "angular_api") -> dict | None:
    """
    Fetch all additional_charges for a booking, sum them, and update the invoice.

    Called at check-out to settle consumption charges (room service, minibar, damages, etc.).
    Returns the updated invoice dict, or None if no invoice exists.
    """
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION

    db = get_database()

    # 1. Fetch all charges for this booking
    charges = list(
        db[CHARGES_COLLECTION].find({"booking_id": booking_id})
    )
    charges_sum = round(sum(c.get("total", 0) or 0 for c in charges), 2)

    if not charges and not db[INVOICES].find_one({"booking_id": booking_id}):
        return None

    # 2. Fetch existing invoice
    inv = db[INVOICES].find_one({"booking_id": booking_id})
    if not inv:
        return None

    inv_id = inv["_id"]

    # 3. Build line_items from charges
    charge_items = []
    for c in charges:
        charge_items.append({
            "type": "additional_charge",
            "charge_id": str(c.get("_id")),
            "concept": c.get("concept", ""),
            "amount": c.get("amount", 0),
            "quantity": c.get("quantity", 1),
            "total": c.get("total", 0),
            "created_at": c.get("created_at", ""),
        })

    # 4. Preserve existing line items (product add-ons) and append new charges
    existing_line_items = inv.get("line_items", []) or []
    # Avoid duplicates: skip charge_ids already in the invoice
    existing_charge_ids = {
        item["charge_id"] for item in existing_line_items
        if isinstance(item, dict) and item.get("type") == "additional_charge" and item.get("charge_id")
    }
    new_items = [item for item in charge_items if item["charge_id"] not in existing_charge_ids]
    if not new_items:
        # All charges already settled in a previous run — skip to avoid double-counting
        return _enrich_invoice(inv)

    combined_line_items = existing_line_items + new_items

    # 5. Recalculate financials
    room_subtotal = inv.get("room_subtotal", 0) or 0
    existing_extras = inv.get("extras_total", 0) or 0
    new_extras = round(existing_extras + charges_sum, 2)
    new_subtotal = round(room_subtotal + new_extras, 2)
    # Recalculate taxes at same rate (16% IVA on new subtotal)
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
                "charge_id": str(c.get("_id")),
                "concept": c.get("concept", ""),
                "amount": c.get("amount", 0),
                "quantity": c.get("quantity", 1),
                "total": c.get("total", 0),
            }
            for c in charges
        ],
        "updated_at": _now(),
    }

    db[INVOICES].update_one(
        {"_id": inv_id},
        {"$set": update_doc},
    )
    db[FACT_INVOICES].update_one(
        {"_id": inv_id},
        {"$set": update_doc},
    )

    # 6. Also update the booking's total_price to reflect charges
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "total_charges": charges_sum,
                "total_price": new_total,
                "updated_at": _now(),
            }
        },
    )

    # 7. Record settlement in status history (only when new charges were actually settled)
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "settled_charges",
        "changed_at": _now(),
        "reason": f"Consumo liquidado: {len(new_items)} cargo(s) por ${charges_sum:.2f}",
        "changed_by": changed_by,
        "is_test": False,
    })

    # Refresh and return
    updated = db[INVOICES].find_one({"_id": inv_id})
    return _enrich_invoice(updated) if updated else None


def create_split_charges_invoice(booking_id: str, *, changed_by: str = "angular_api") -> dict | None:
    """
    Create a separate invoice for additional charges only (split by charge type).

    Used at check-out when split_invoice=True. Leaves the room invoice untouched
    and creates a new invoice exclusively for additional charges (room service,
    minibar, damages, etc.).

    Returns the new charges invoice dict, or None if no charges exist.
    """
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION

    db = get_database()

    # 1. Fetch all charges for this booking
    charges = list(
        db[CHARGES_COLLECTION].find({"booking_id": booking_id})
    )
    if not charges:
        return None

    charges_sum = round(sum(c.get("total", 0) or 0 for c in charges), 2)

    # 2. Fetch booking data
    booking = _find_booking(booking_id)
    if not booking:
        return None

    # 3. Fetch existing room invoice to link as parent
    room_inv = db[INVOICES].find_one({"booking_id": booking_id, "split_type": {"$ne": "charges_only"}})
    room_inv_id = room_inv["_id"] if room_inv else None

    # 4. Build line_items from charges
    charge_items = []
    for c in charges:
        charge_items.append({
            "type": "additional_charge",
            "charge_id": str(c.get("_id")),
            "concept": c.get("concept", "") or c.get("item_name", ""),
            "amount": c.get("amount", 0),
            "quantity": c.get("quantity", 1),
            "total": c.get("total", 0),
            "created_at": c.get("created_at", ""),
        })

    # 5. Calculate financials for charges-only invoice
    extras_total = charges_sum
    subtotal = charges_sum
    taxes = round(subtotal * 0.16, 2)  # 16% IVA
    total = round(subtotal + taxes, 2)

    # 6. Create the charges invoice
    inv_doc = {
        "booking_id": booking.get("booking_id") or booking_id,
        "prop_id": booking.get("prop_id", 0),
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
                "charge_id": str(c.get("_id")),
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

    # 7. Mark the room invoice as room_only (if not already marked)
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

    # 8. Update booking total to include charges
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "total_charges": charges_sum,
                "split_invoice": True,
                "updated_at": _now(),
            }
        },
    )

    # 9. Record settlement in status history
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "split_charges_invoice",
        "changed_at": _now(),
        "reason": f"Factura de consumos separada creada: {len(charges)} cargo(s) por ${charges_sum:.2f}",
        "changed_by": changed_by,
        "is_test": False,
    })

    # Refresh and return
    inserted_id = inv_doc.get("_id")
    if not inserted_id:
        # _write_both modifies the doc in-place, look for inserted_id
        pass
    updated = db[INVOICES].find_one({"invoice_number": inv_doc["invoice_number"]})
    return _enrich_invoice(updated) if updated else None


def _enrich_payment(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["booking_id"] = str(doc.get("booking_id", ""))
    doc["invoice_id"] = str(doc["invoice_id"]) if doc.get("invoice_id") else None
    for f in ("paid_at",):
        doc[f] = _fmt(doc.get(f))
    return doc
