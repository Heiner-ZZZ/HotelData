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
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from src.app.core.resolvers import resolve_hotel_id
from src.database.connection import get_database

FOLIO_COLLECTION = "guest_folios"

# ── Helpers ──


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_object_id_ref(value: Any) -> Any:
    """Normalize a Mongo ``_id`` reference to its canonical BSON type.

    Hex strings (the wire format the frontend and ``str()`` callers produce)
    become ``ObjectId``; ``None`` and already-``ObjectId`` values pass
    through untouched. Non-hex strings (garbage) pass through as-is so
    readers that compare against business keys are unaffected.
    """
    if value is None or isinstance(value, ObjectId):
        return value
    if isinstance(value, str) and ObjectId.is_valid(value.strip()):
        return ObjectId(value.strip())
    return value


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
        except InvalidId:
            pass
    return booking


def resolve_checkout_at(db: Any, booking_id: str) -> datetime | None:
    """Resolve checkout evidence from actual fields or immutable status history."""
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"check_out_date_actual": 1, "check_out_time_actual": 1},
    ) or {}
    date_value = booking.get("check_out_date_actual")
    time_value = booking.get("check_out_time_actual")
    if date_value and time_value:
        try:
            return datetime.fromisoformat(f"{str(date_value)[:10]}T{str(time_value)[:8]}")
        except ValueError:
            pass
    history = db.booking_status_history.find_one(
        {"booking_id": booking_id, "status": "checked_out", "changed_at": {"$exists": True}},
        {"changed_at": 1},
        sort=[("changed_at", -1)],
    )
    changed_at = (history or {}).get("changed_at")
    if isinstance(changed_at, datetime):
        return changed_at.replace(tzinfo=None)
    return None


def get_folio_posting_trace(
    db: Any,
    *,
    booking_id: str,
    reference_id: str,
    reference_type: str,
) -> dict[str, Any] | None:
    """Return stable source references for one committed folio posting.

    Folio postings are the operational source of truth for guest charges. The
    source document should retain the same links after a successful post so a
    reconciliation reader does not have to rediscover them by scanning an
    embedded array. This helper is read-only and deliberately does not create
    any financial event.
    """
    folio = db[FOLIO_COLLECTION].find_one({
        "booking_id": booking_id,
        "postings": {"$elemMatch": {
            "reference_id": reference_id,
            "reference_type": reference_type,
        }},
    })
    if not folio:
        return None
    posting = next(
        (
            item for item in folio.get("postings", [])
            if item.get("reference_id") == reference_id
            and item.get("reference_type") == reference_type
        ),
        None,
    )
    if not posting or not posting.get("posting_id"):
        return None
    return {
        "folio_id": folio["_id"],
        "folio_number": folio.get("folio_number"),
        "posting_id": posting["posting_id"],
        "posting_reference": reference_id,
        "posting_type": posting.get("type"),
        "posting_reference_type": reference_type,
    }


def _enrich_folio(doc: dict) -> dict:
    """Convert _id to id and format datetimes."""
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "updated_at", "closed_at"):
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


def _attach_invoice_reconciliation(db: Any, doc: dict, enriched: dict) -> None:
    """Attach invoice coverage metadata used by the folio receipt.

    ``invoice_covered_subtotal`` sums every non-cancelled invoice for the
    booking (main + complementary invoices), matching the check-out detail's
    reconciliation contract. The folio page can then show the same warning in
    both the live view and its printed/PDF receipt without guessing from labels.
    """
    booking_id = str(doc.get("booking_id") or "")
    if not booking_id:
        return

    invoices = list(db.reservation_invoices.find(
        {"booking_id": booking_id},
        {"invoice_number": 1, "subtotal": 1, "status": 1, "issued_at": 1},
    ).sort("issued_at", -1))
    if not invoices:
        return

    active_invoices = [invoice for invoice in invoices if invoice.get("status") != "cancelled"]
    if not active_invoices:
        return

    covered_subtotal = round(sum(
        float(invoice.get("subtotal", 0) or 0) for invoice in active_invoices
    ), 2)
    linked_invoice_id = str(doc.get("invoice_id") or "")
    primary = next(
        (invoice for invoice in active_invoices if str(invoice.get("_id")) == linked_invoice_id),
        None,
    ) or active_invoices[0]

    # Some historical check-outs created the invoice before the folio FK was
    # backfilled. The booking-scoped invoice is still the authoritative source
    # for the printed receipt, so expose it as the effective folio invoice
    # without mutating Mongo from this read path.
    enriched["has_invoice"] = True
    if not doc.get("invoice_id") and primary.get("_id"):
        enriched["invoice_id"] = primary["_id"]
    enriched["invoice_number"] = primary.get("invoice_number") or ""
    enriched["invoice_status"] = primary.get("status") or ""
    enriched["invoice_subtotal"] = round(float(primary.get("subtotal", 0) or 0), 2)
    enriched["invoice_covered_subtotal"] = covered_subtotal


# ── Core Operations ──


def _sync_issued_invoice_line_item(
    db: Any,
    booking_id: str,
    item: dict,
    *,
    removing: bool = False,
) -> None:
    """Add/remove a folio-mirrored line item on the active issued invoice.

    Best-effort (never fails the folio posting): an issued invoice that
    exists for the booking is kept in sync with the booking's line items so
    the guest bill reflects folio charges without a manual rebuild.
    """
    try:
        item_id = str(item.get("item_id") or "")
        if not item_id:
            return
        inv = db.reservation_invoices.find_one(
            {"booking_id": booking_id, "status": "issued"},
            {"line_items": 1, "room_subtotal": 1},
        )
        if not inv:
            return
        existing = inv.get("line_items") or []
        if removing:
            remaining = [li for li in existing if not (isinstance(li, dict) and li.get("item_id") == item_id)]
        else:
            already = any(isinstance(li, dict) and li.get("item_id") == item_id for li in existing)
            if already:
                return
            remaining = existing + [item]
        extras_total = round(sum(
            float(li.get("total", 0) or 0)
            for li in remaining
            if isinstance(li, dict) and li.get("type") != "room"
        ), 2)
        room_subtotal = float(inv.get("room_subtotal", 0) or 0)
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
            }
        }
        db.reservation_invoices.update_one({"_id": inv["_id"]}, update)
        db.fact_reservation_invoices.update_one({"_id": inv["_id"]}, update)
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Failed to sync invoice line item for booking %s", booking_id)


def _mirror_folio_charge_to_booking(db: Any, booking_id: str, posting: dict) -> None:
    """Mirror a folio charge into the booking's line items.

    Direct folio charges ("Agregar cargo", reference_type ``manual``) must
    appear in ``booking.line_items`` so the reservation detail and invoice
    see them — closing the two-source gap. Postings that already have their
    own booking representation (hotel products, reservation-time additional
    charges) are skipped to avoid double counting.
    """
    if posting.get("type") != "charge":
        return
    # Only direct folio charges from the stay view ("Agregar cargo") are
    # mirrored. Every other reference_type belongs to a dedicated flow that
    # already has its own booking/invoice representation (hotel products,
    # reservation-time additional charges and their revisions, no-show
    # penalties, payments, the initial room charge) and must not be mirrored
    # to avoid double counting.
    reference_type = str(posting.get("reference_type") or "")
    if reference_type != "manual":
        return
    item_id = str(posting.get("posting_id") or "")
    if not item_id:
        return
    already = db.booking_orders.find_one(
        {"booking_id": booking_id, "line_items.item_id": item_id},
        {"_id": 1},
    )
    if already:
        return
    line_item = {
        "item_id": item_id,
        "type": "folio_charge",
        "name": posting.get("concept", ""),
        "category": posting.get("category", "Otros"),
        "quantity": int(posting.get("quantity", 1) or 1),
        "unit_price": round(float(posting.get("unit_price", posting.get("amount", 0)) or 0), 2),
        "total": round(float(posting.get("amount", 0) or 0), 2),
        "reference_id": str(posting.get("reference_id") or ""),
        "reference_type": reference_type,
        "added_at": posting.get("posted_at"),
        "source": "folio",
    }
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$push": {"line_items": line_item},
            "$inc": {"total_charges": line_item["total"]},
        },
    )
    _sync_issued_invoice_line_item(db, booking_id, line_item)


def _unmirror_folio_charge_from_booking(db: Any, booking_id: str, posting: dict) -> None:
    """Remove the booking line item mirrored from a folio charge on reversal.

    A ``charge_reversal`` is a compensating event: the original charge stays
    in the folio history, but the booking line item it mirrored (keyed by the
    original posting id passed as ``reference_id``) is removed and totals are
    restored. Best-effort — a no-op when no mirror exists.
    """
    reference_id = str(posting.get("reference_id") or "")
    if not reference_id:
        return
    item = db.booking_orders.find_one(
        {"booking_id": booking_id, "line_items.item_id": reference_id},
        {"_id": 0, "line_items": 1},
    )
    target = next(
        (li for li in (item or {}).get("line_items", []) if li.get("item_id") == reference_id),
        None,
    )
    if not target:
        return
    total = float(target.get("total", 0) or 0)
    db.booking_orders.update_one(
        {"booking_id": booking_id, "line_items.item_id": reference_id},
        {
            "$pull": {"line_items": {"item_id": reference_id}},
            "$inc": {"total_charges": -total},
        },
    )
    _sync_issued_invoice_line_item(db, booking_id, target, removing=True)


def _reconcile_pending_additional_charges(db: Any, booking_id: str, prop_id: int) -> None:
    """Post pre-folio charges once the guest folio exists.

    Reservation-time amenities can be recorded before check-in creates the
    folio. Reconcile only pending charges, and use the charge ObjectId as the
    stable posting reference so retries cannot invent a second financial event.
    """
    pending = db.additional_charges.find({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "posting_status": {"$in": ["pending", "posting_failed"]},
    }).sort("_id", 1)
    for charge in pending:
        charge_id = str(charge["_id"])
        already_posted = db.guest_folios.find_one({
            "booking_id": booking_id,
            "postings": {"$elemMatch": {
                "reference_id": charge_id,
                "reference_type": "additional_charge",
            }},
        }, {"_id": 1})
        if already_posted:
            trace = get_folio_posting_trace(
                db,
                booking_id=booking_id,
                reference_id=charge_id,
                reference_type="additional_charge",
            )
            update = {"posting_status": "posted", "posting_error": None}
            if trace:
                update.update(trace)
                from src.app.modules.housekeeping.service.lifecycle.charges import _record_charge_posted_event
                event = _record_charge_posted_event(
                    prop_id=prop_id,
                    booking_id=booking_id,
                    charge_id=charge_id,
                    total=float(charge.get("total", charge.get("amount", 0)) or 0),
                    trace=trace,
                    changed_by="folio_reconciliation",
                )
                update["domain_event_id"] = event.get("event_id") if event else None
                update["domain_event_status"] = "posted" if event else "failed"
            db.additional_charges.update_one(
                {"_id": charge["_id"]},
                {"$set": update},
            )
            continue

        try:
            posted = post_to_folio(
                booking_id,
                posting_type="charge",
                category=charge.get("category", "Otros"),
                concept=charge.get("concept", ""),
                amount=float(charge.get("total", charge.get("amount", 0)) or 0),
                quantity=int(charge.get("quantity", 1) or 1),
                reference_id=charge_id,
                reference_type="additional_charge",
            )
            if posted is None:
                raise RuntimeError("guest folio is not open")
            trace = get_folio_posting_trace(
                db,
                booking_id=booking_id,
                reference_id=charge_id,
                reference_type="additional_charge",
            )
            if not trace:
                raise RuntimeError("folio posting committed without trace")
            update = {"posting_status": "posted", "posting_error": None}
            update.update(trace)
            from src.app.modules.housekeeping.service.lifecycle.charges import _record_charge_posted_event
            event = _record_charge_posted_event(
                prop_id=prop_id,
                booking_id=booking_id,
                charge_id=charge_id,
                total=float(charge.get("total", charge.get("amount", 0)) or 0),
                trace=trace,
                changed_by="folio_reconciliation",
            )
            update["domain_event_id"] = event.get("event_id") if event else None
            update["domain_event_status"] = "posted" if event else "failed"
            db.additional_charges.update_one(
                {"_id": charge["_id"]},
                {"$set": update},
            )
        except Exception as exc:
            db.additional_charges.update_one(
                {"_id": charge["_id"]},
                {"$set": {"posting_status": "posting_failed", "posting_error": str(exc)}},
            )


def _reconcile_confirmed_payments(db: Any, booking_id: str) -> None:
    """Attach confirmed payments created before the folio existed.

    Payment creation is allowed before check-in for online/pre-authorized
    flows. Once the folio is created, replay only payments without their stable
    payment reference in the folio postings. This makes retries idempotent and
    preserves the original payment document as the source of truth.
    """
    for payment in db.reservation_payments.find({
        "booking_id": booking_id,
        "status": "confirmed",
    }).sort("_id", 1):
        payment_ref = str(payment.get("reference") or payment.get("_id"))
        already_posted = db[FOLIO_COLLECTION].find_one({
            "booking_id": booking_id,
            "postings": {"$elemMatch": {
                "reference_id": payment_ref,
                "reference_type": "payment",
            }},
        }, {"_id": 1})
        if already_posted:
            continue
        posted = post_to_folio(
            booking_id,
            posting_type="payment",
            category=str(payment.get("method") or "Payment").title(),
            concept=f"Pago {payment_ref}",
            amount=float(payment.get("amount", 0) or 0),
            reference_id=payment_ref,
            reference_type="payment",
        )
        if posted is None:
            # Keep the payment traceable but explicit: it is confirmed at the
            # gateway level and remains unapplied until an operator resolves
            # the mismatch; never pretend it was charged to the folio.
            db.reservation_payments.update_one(
                {"_id": payment["_id"], "status": "confirmed"},
                {"$set": {
                    "status": "unapplied",
                    "unapplied_reason": "folio_balance_or_closed",
                    "updated_at": _now(),
                }},
            )
            db.fact_reservation_payments.update_one(
                {"_id": payment["_id"], "status": "confirmed"},
                {"$set": {
                    "status": "unapplied",
                    "unapplied_reason": "folio_balance_or_closed",
                    "updated_at": _now(),
                }},
            )


def _canonicalize_folio_category(category: str, category_id: str = "") -> tuple[str, str]:
    """Resolve a folio category through the canonical id/label catalog path."""
    if category_id:
        entry = next((c for c in FOLIO_CATEGORIES if c["id"] == category_id), None)
        return (entry["label"], category_id) if entry is not None else (category, category_id)

    entry = next((c for c in FOLIO_CATEGORIES if c["id"] == category), None)
    return (entry["label"], category) if entry is not None else (category, "")


def create_folio(booking_id: str, *, shift_id: str | None = None) -> dict | None:
    """Create a new folio for a booking at check-in.

    Automatically posts the initial room charge from the booking.
    Returns the folio dict, or None if booking not found.

    ``shift_id`` (optional) ties the folio to the active cash shift when the
    check-in was a front-desk operation; web-channel stays keep it null.
    """
    booking = _find_booking(booking_id)
    if not booking:
        return None

    db = get_database()

    # Check if folio already exists
    existing = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    if existing:
        _reconcile_pending_additional_charges(db, booking_id, prop_id=int(booking.get("prop_id", 0) or 0))
        _reconcile_confirmed_payments(db, booking_id)
        refreshed = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
        return _enrich_folio(refreshed) if refreshed else None

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

    # Initial posting: room charge. Use the same canonical category resolver as
    # post_to_folio so the first posting carries the catalog id as well.
    room_category, room_category_id = _canonicalize_folio_category(
        "Habitación", "habitacion"
    )
    initial_posting = {
        "posting_id": ObjectId(),
        "type": "room",
        "category": room_category,
        "category_id": room_category_id,
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
        "shift_id": ObjectId(shift_id) if shift_id else None,
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
    _reconcile_pending_additional_charges(db, booking_id, prop_id=prop_id)
    _reconcile_confirmed_payments(db, booking_id)
    refreshed = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    return _enrich_folio(refreshed) if refreshed else None


def _resolve_created_shift(doc: dict) -> dict | None:
    """Resolve the shift that opened the folio (check-in cash shift).

    ``create_folio`` ties the folio to the active cash shift at check-in via
    the ``shift_id`` FK. Returns the responsible cashier + shift label, or
    ``None`` when the folio has no shift (web-channel stays) or the shift
    cannot be resolved — the UI then shows no attribution instead of failing.
    """
    raw_shift_id = doc.get("shift_id")
    if not raw_shift_id:
        return None
    try:
        from src.app.modules.reception import get_shift
        from src.app.modules.reception.shifts import get_shift_labels
        shift_id = str(raw_shift_id)
        shift_doc = get_shift(shift_id)
        if not shift_doc:
            return None
        shift_type = shift_doc.get("shift_type") or ""
        prop_id = int(doc.get("prop_id") or 0)
        return {
            "shift_id": shift_id,
            "shift_type": shift_type,
            "shift_label": get_shift_labels(prop_id).get(shift_type, shift_type) or None,
            "employee": shift_doc.get("employee"),
            "opened_by": shift_doc.get("opened_by"),
            "start_time": shift_doc.get("start_time"),
        }
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("Failed to resolve created_shift for folio %s", doc.get("booking_id"))
        return None


def get_folio(booking_id: str) -> dict | None:
    """Get the active folio for a booking by booking_id.

    Re-resolves hotel_label and check-in/out times from the booking
    for backward compatibility with folios created before these fields
    were stored.
    """
    db = get_database()
    doc = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    if not doc:
        # Recovery path for no-shows processed before the folio insert became
        # collision-safe: the booking state and penalty are already persisted,
        # so recreate the missing penalty folio idempotently before returning
        # the billing 404. Normal bookings remain read-only here.
        booking = _find_booking(booking_id)
        if booking and booking.get("stay_status") == "no_show":
            from src.app.modules.reservations.service.no_show import (
                ensure_no_show_folio,
            )
            ensure_no_show_folio(db, booking)
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

    enriched = _enrich_folio(doc)
    enriched["created_shift"] = _resolve_created_shift(doc)
    _attach_invoice_reconciliation(db, doc, enriched)
    return enriched


def get_folio_by_id(folio_id: str) -> dict | None:
    """Get a folio by its ObjectId."""
    try:
        from bson.errors import InvalidId
        doc_id = ObjectId(folio_id)
    except (InvalidId, Exception):
        return None
    db = get_database()
    doc = db[FOLIO_COLLECTION].find_one({"_id": doc_id})
    if not doc:
        return None
    enriched = _enrich_folio(doc)
    enriched["created_shift"] = _resolve_created_shift(doc)
    _attach_invoice_reconciliation(db, doc, enriched)
    return enriched


def post_to_folio(
    booking_id: str,
    *,
    posting_type: str = "charge",
    category: str = "Otros",
    category_id: str = "",
    concept: str = "",
    amount: float = 0.0,
    quantity: int = 1,
    unit_price: float | None = None,
    reference_id: str = "",
    reference_type: str = "additional_charge",
    posted_at: datetime | None = None,
    shift_id: str | None = None,
    shift_attribution: dict | None = None,
) -> dict | None:
    """Post a transaction to the folio.

    Supports types: charge, discount, payment, adjustment.
    Automatically recalculates total_charges, total_discounts,
    total_payments, and total_due on the folio.

    ``category_id`` (optional) is the canonical catalog id (``FOLIO_CATEGORIES``).
    When provided, the label is resolved from the catalog and stored in
    ``category`` — automatic postings (late check-out, early check-in,
    no-show penalty) use the id so the frontend can resolve label/icon
    without string-matching labels.

    ``shift_id``/``shift_attribution`` (optional) stamp the responsible
    cashier shift on the posting entry — used by the front-desk routes so
    every money movement is attributable.

    Returns the updated folio, or None if not found.
    """
    db = get_database()

    # Algunos callers históricos guardan el id del catálogo en ``category``
    # (ej. los postings manuales del formulario). La misma ruta canónica sirve
    # tanto para resolver ese quirk como para los ids explícitos.
    category, category_id = _canonicalize_folio_category(category, category_id)

    amount = round(amount, 2)
    if unit_price is None:
        unit_price = round(amount / max(quantity, 1), 2)

    now = posted_at or _now()
    if reference_id and reference_type:
        existing = db[FOLIO_COLLECTION].find_one(
            {
                "booking_id": booking_id,
                "postings": {"$elemMatch": {
                    "reference_id": reference_id,
                    "reference_type": reference_type,
                }},
            },
        )
        if existing is not None:
            matching = next(
                (
                    posting for posting in existing.get("postings", [])
                    if posting.get("reference_id") == reference_id
                    and posting.get("reference_type") == reference_type
                ),
                None,
            )
            if matching and (
                round(float(matching.get("amount", 0) or 0), 2) != amount
                or int(matching.get("quantity", 1) or 1) != int(quantity or 1)
                or matching.get("type") != posting_type
            ):
                return None
            return _enrich_folio(existing)

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
    if category_id:
        posting["category_id"] = category_id
    if shift_id:
        try:
            posting["shift_id"] = ObjectId(shift_id)
        except Exception:
            posting["shift_id"] = shift_id
    if shift_attribution:
        for key in ("shift_employee", "shift_opened_by", "shift_opened_by_id", "shift_type"):
            if shift_attribution.get(key) is not None:
                posting[key] = shift_attribution[key]

    # Build atomic $inc fields — total_due is incremented atomically
    # alongside its component fields, eliminating the TOCTOU race.
    inc_fields: dict[str, float] = {}
    if posting_type == "charge":
        inc_fields["total_charges"] = amount
        inc_fields["total_due"] = amount
    elif posting_type == "refund":
        # A refund reverses a prior payment without rewriting history. Keep the
        # original payment posting and add a compensating event.
        inc_fields["total_payments"] = -abs(amount)
        inc_fields["total_due"] = abs(amount)
    elif posting_type == "charge_reversal":
        # A voided charge is a compensating event: preserve the original
        # charge posting and decrease the charge/due accumulators atomically.
        inc_fields["total_charges"] = -abs(amount)
        inc_fields["total_due"] = -abs(amount)
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

    # Refunds and charge reversals are immutable compensating events and may
    # be recorded against a closed folio. Ordinary charges/payments still
    # require an open folio.
    folio_query: dict[str, Any] = {"booking_id": booking_id}
    if posting_type not in {"refund", "charge_reversal"}:
        folio_query["status"] = "open"
    if reference_id and reference_type:
        # The preliminary read is only an optimization. Repeating the
        # idempotency predicate in the atomic update prevents concurrent
        # retries from appending the same event twice.
        folio_query["postings"] = {"$not": {"$elemMatch": {
            "reference_id": reference_id,
            "reference_type": reference_type,
        }}}
    if posting_type == "payment":
        # Do not silently floor an overpayment to zero.
        folio_query["total_due"] = {"$gte": amount}

    result = db[FOLIO_COLLECTION].find_one_and_update(
        folio_query,
        {
            "$push": {"postings": posting},
            "$inc": {**inc_fields, "posting_count": 1},
            "$set": {"updated_at": now},
        },
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        # A concurrent retry may have won the atomic append after the
        # preliminary idempotency read. Return that committed event instead of
        # making the caller treat a harmless duplicate as a posting failure.
        if reference_id and reference_type:
            committed = db[FOLIO_COLLECTION].find_one({
                "booking_id": booking_id,
                "postings": {"$elemMatch": {
                    "reference_id": reference_id,
                    "reference_type": reference_type,
                }},
            })
            if committed is not None:
                return _enrich_folio(committed)
        return None

    if result:
        try:
            from src.app.modules.financial_reconciliation.domain_events import append_domain_event
            folio_id = str(result.get("_id", ""))
            posting_id = str(posting.get("posting_id", ""))
            append_domain_event(
                prop_id=int(result.get("prop_id", 0) or 0),
                event_type=f"guest_ar.folio_posting.{posting_type}",
                aggregate_type="guest_ar",
                aggregate_id=folio_id,
                idempotency_key=f"live:folio-posting:{folio_id}:{posting_id}",
                payload={"booking_id": booking_id, "amount": amount, "posting_type": posting_type, "reference_id": reference_id},
                source_collection=FOLIO_COLLECTION,
                source_id=folio_id,
            )
        except Exception:
            # Financial posting remains the source of truth; reconciliation
            # will surface a missing event if the event store is unavailable.
            pass
        # Keep booking.line_items in sync with the folio (bidirectional
        # reconciliation). Manual charges are mirrored; reversals remove the
        # mirror. Best-effort — the folio posting already succeeded.
        try:
            if posting.get("type") == "charge_reversal":
                _unmirror_folio_charge_from_booking(db, booking_id, posting)
            else:
                _mirror_folio_charge_to_booking(db, booking_id, posting)
        except Exception:
            __import__("logging").getLogger(__name__).exception(
                "Failed to mirror folio charge for booking %s", booking_id
            )
    return _enrich_folio(result) if result else None


def _ensure_settlement_indexes(db: Any) -> None:
    """Ensure settlement idempotency indexes without renaming legacy indexes."""
    key = [("booking_id", 1), ("idempotency_key", 1)]
    for collection_name in ("folio_settlement_events", "fact_folio_settlement_events"):
        collection = db[collection_name]
        existing = next(
            (
                index for index in collection.list_indexes()
                if list(index.get("key", {}).items()) == key
                and index.get("unique") is True
            ),
            None,
        )
        if existing is None:
            collection.create_index(key, unique=True, name="idx_folio_settlement_booking_key")


def _write_settlement_event(db: Any, event: dict) -> None:
    """Persist the operational settlement event and its denormalized mirror."""
    db.folio_settlement_events.insert_one(event)
    db.fact_folio_settlement_events.replace_one(
        {"_id": event["_id"]},
        dict(event),
        upsert=True,
    )


def is_historical_cash_shift_eligible(shift: dict, booking_id: str) -> bool:
    """Accept a reconstructed shift or the closed shift that recorded checkout.

    Historical cash reconciliation must never use an arbitrary closed drawer.
    A real checkout transaction is equally strong evidence when the checkout
    already belongs to an existing operational shift.
    """
    if not shift or shift.get("status") != "closed":
        return False
    category = shift.get("metadata", {}).get("reconciliation", {}).get("category")
    if category == "historical_reconstructed":
        return True
    return any(
        str(transaction.get("booking_id")) == str(booking_id)
        and str(transaction.get("type", "")).lower() in {"check_out", "checkout"}
        for transaction in shift.get("transactions", [])
    )


def _parse_settlement_at(value: Any) -> datetime | None:
    """Parse an optional effective settlement timestamp in UTC."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("settlement_at debe ser una fecha ISO válida") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _link_settlement_payment_to_shift(
    db: Any,
    *,
    shift_id: str,
    payment: dict,
    booking_id: str,
    folio_id: ObjectId,
    effective_at: datetime,
) -> None:
    """Add a historical payment to its reconstructed shift exactly once."""
    try:
        shift_oid = ObjectId(shift_id)
    except Exception as exc:
        raise ValueError("shift_id histórico inválido para el pago") from exc
    shift = db["reception_shifts"].find_one({"_id": shift_oid})
    if not shift:
        raise ValueError("No existe el turno histórico asociado al checkout")
    if int(shift.get("prop_id", 0) or 0) != int(payment.get("prop_id", 0) or 0):
        raise ValueError("El turno histórico no pertenece al hotel del folio")

    payment_id = payment.get("_id")
    if payment_id is None and payment.get("id"):
        payment_id = ObjectId(str(payment["id"]))
    if payment_id is None:
        raise ValueError("El pago histórico no tiene identificador")
    transaction_id = f"settlement:{payment.get('reference', payment_id)}"
    existing = db["reception_shifts"].find_one(
        {"_id": shift_oid, "transactions.transaction_id": transaction_id},
        {"_id": 1},
    )
    if existing:
        db["reception_shifts"].update_one(
            {"_id": shift_oid},
            {
                "$addToSet": {
                    "payment_ids": payment_id,
                    "folio_ids": folio_id,
                },
                "$set": {
                    "transactions.$[txn].folio_id": folio_id,
                    "transactions.$[txn].actor_user_id": payment.get("actor_user_id"),
                    "transactions.$[txn].actor_username": payment.get("actor_username"),
                },
            },
            array_filters=[{"txn.transaction_id": transaction_id}],
        )
        return

    transaction = {
        "transaction_id": transaction_id,
        "type": "payment",
        "booking_id": booking_id,
        "folio_id": folio_id,
        "payment_id": payment_id,
        "actor_user_id": payment.get("actor_user_id"),
        "actor_username": payment.get("actor_username"),
        "amount": round(float(payment.get("amount", 0) or 0), 2),
        "payment_method": payment.get("method", ""),
        "timestamp": effective_at.isoformat(),
        "description": f"Pago histórico de folio {payment.get('reference', '')}",
        "evidence_reference": payment.get("evidence_reference"),
    }
    db["reception_shifts"].update_one(
        {"_id": shift_oid, "transactions.transaction_id": {"$ne": transaction_id}},
        {
            "$addToSet": {
                "payment_ids": payment_id,
                "folio_ids": folio_id,
            },
            "$push": {"transactions": transaction},
            "$inc": {
                "total_collected": transaction["amount"],
                "payment_breakdown.cash" if payment.get("method") in {"cash", "efectivo"} else "payment_breakdown.other": transaction["amount"],
                "payment_breakdown.total": transaction["amount"],
            },
        },
    )


def _record_settlement_audit(
    *,
    prop_id: int,
    booking_id: str,
    settlement_type: str,
    amount: float,
    changed_by: str,
    idempotency_key: str,
    effective_at: datetime | None,
    evidence_reference: str | None,
    actor_user_id: ObjectId | None = None,
) -> None:
    """Persist the settlement action independently of the API request log."""
    try:
        from src.app.modules.partner.services.audit import register_action
        register_action(
            prop_id=prop_id,
            entity_type="folio_settlement",
            entity_id=booking_id,
            action=settlement_type,
            summary=f"Resolución de folio por {settlement_type}: ${amount:,.2f}",
            changed_by=changed_by,
            metadata={
                "idempotency_key": idempotency_key,
                "effective_at": effective_at,
                "evidence_reference": evidence_reference,
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
            },
        )
    except Exception:
        # The settlement event remains the durable operational audit if the
        # best-effort universal audit writer is temporarily unavailable.
        pass


def settle_folio(
    booking_id: str,
    payload: dict,
    *,
    changed_by: str = "system",
    actor_user_id: ObjectId | str | None = None,
    shift_id: str | None = None,
) -> dict | None:
    """Resolve a positive folio balance through one explicit outcome.

    ``payment`` records a confirmed payment (partial payments keep the folio
    open); ``write_off`` and ``external_settlement`` require a reason plus an
    approval reference. A full non-cash outcome appends an immutable folio
    event, posts a balanced GL pair, and marks the folio settled without
    pretending that cash was received. ``idempotency_key`` is mandatory so a
    retry cannot duplicate money, ledger rows, or settlement documents.
    """
    db = get_database()
    _ensure_settlement_indexes(db)
    actor_oid = None
    if actor_user_id:
        try:
            actor_oid = actor_user_id if isinstance(actor_user_id, ObjectId) else ObjectId(str(actor_user_id))
        except Exception as exc:
            raise ValueError("actor_user_id inválido") from exc

    settlement_type = str(payload.get("settlement_type") or "").strip().lower()
    if settlement_type not in {"payment", "write_off", "external_settlement"}:
        raise ValueError("settlement_type debe ser payment, write_off o external_settlement")
    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if not idempotency_key:
        raise ValueError("idempotency_key es requerido")

    existing_event = db.folio_settlement_events.find_one({
        "booking_id": booking_id,
        "idempotency_key": idempotency_key,
    })
    if existing_event:
        current = db[FOLIO_COLLECTION].find_one({"_id": existing_event["folio_id"]})
        return _enrich_folio(current) if current else None

    folio = db[FOLIO_COLLECTION].find_one({
        "booking_id": booking_id,
        "status": "open",
        "total_due": {"$gt": 0.005},
    })
    if not folio:
        return None

    due = round(float(folio.get("total_due", 0) or 0), 2)
    now = _now()
    reason = str(payload.get("reason") or "").strip()
    approval_reference = str(payload.get("approval_reference") or "").strip()
    external_reference = str(payload.get("external_reference") or "").strip()
    evidence_type = str(payload.get("evidence_type") or "").strip() or None
    evidence_reference = str(payload.get("evidence_reference") or "").strip() or None
    effective_at = _parse_settlement_at(payload.get("settlement_at"))

    if settlement_type == "payment" and effective_at is not None:
        if not shift_id and str(payload.get("method") or "").strip().lower() in {"cash", "efectivo"}:
            raise ValueError("Un pago histórico en efectivo requiere el turno del checkout")
        if not evidence_reference:
            raise ValueError("evidence_reference es obligatorio para un pago histórico")
        evidence_type = evidence_type or "manager_attestation"

    if settlement_type in {"write_off", "external_settlement"}:
        if not reason or not approval_reference:
            raise ValueError("reason y approval_reference son obligatorios para una liquidación aprobada")
        if settlement_type == "external_settlement" and not external_reference:
            raise ValueError("external_reference es obligatorio para una liquidación externa")

        source = "folio_write_off" if settlement_type == "write_off" else "folio_external_settlement"
        debit_code, debit_name = (
            ("6800", "Gasto por cuentas incobrables")
            if settlement_type == "write_off"
            else ("6790", "Pérdida por liquidación externa autorizada")
        )
        from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
        ledger_reference = post_journal_entry(
            amount=due,
            dr_account_code=debit_code,
            dr_account_name=debit_name,
            cr_account_code="1030",
            cr_account_name="Cuentas por Cobrar Huéspedes",
            description=f"Liquidación de folio {folio.get('folio_number', booking_id)} — {reason}",
            prop_id=int(folio.get("prop_id", 0) or 0),
            source=source,
            source_id=idempotency_key,
            booking_id=booking_id,
        )

        posting = {
            "posting_id": ObjectId(),
            "type": settlement_type,
            "category": "Liquidación",
            "concept": reason,
            "amount": due,
            "quantity": 1,
            "unit_price": due,
            "reference_id": idempotency_key,
            "reference_type": settlement_type,
            "posted_at": now,
        }
        updated = db[FOLIO_COLLECTION].find_one_and_update(
            {
                "_id": folio["_id"],
                "status": "open",
                "total_due": due,
                "postings": {"$not": {"$elemMatch": {"reference_id": idempotency_key}}},
            },
            {"$push": {"postings": posting}, "$inc": {"posting_count": 1}, "$set": {
                "status": "written_off" if settlement_type == "write_off" else "settled",
                "total_due": 0.0,
                "settlement_type": settlement_type,
                "settlement_amount": due,
                "settlement_reason": reason,
                "approval_reference": approval_reference,
                "external_reference": external_reference or None,
                "settled_at": now,
                "settled_by": changed_by,
                "settled_by_user_id": actor_oid,
                "updated_at": now,
            }},
            return_document=ReturnDocument.AFTER,
        )
        if not updated:
            current = db[FOLIO_COLLECTION].find_one({"_id": folio["_id"]})
            return _enrich_folio(current) if current else None

        event = {
            "_id": ObjectId(),
            "booking_id": booking_id,
            "folio_id": folio["_id"],
            "prop_id": folio.get("prop_id", 0),
            "folio_number": folio.get("folio_number", ""),
            "settlement_type": settlement_type,
            "amount": due,
            "reason": reason,
            "approval_reference": approval_reference,
            "external_reference": external_reference or None,
            "idempotency_key": idempotency_key,
            "ledger_reference": ledger_reference,
            "status": "written_off" if settlement_type == "write_off" else "settled",
            "changed_by": changed_by,
            "actor_user_id": actor_oid,
            "created_at": now,
        }
        try:
            _write_settlement_event(db, event)
        except Exception:
            # Do not hide a committed settlement behind a duplicate retry. The
            # unique key means the next call will recover the event if another
            # worker won the race; a real persistence failure is explicit.
            if not db.folio_settlement_events.find_one({"booking_id": booking_id, "idempotency_key": idempotency_key}):
                raise
        _record_settlement_audit(
            prop_id=int(folio.get("prop_id", 0) or 0),
            booking_id=booking_id,
            settlement_type=settlement_type,
            amount=due,
            changed_by=changed_by,
            idempotency_key=idempotency_key,
            effective_at=effective_at,
            evidence_reference=evidence_reference,
            actor_user_id=actor_oid,
        )
        return _enrich_folio(updated)

    amount = round(float(payload.get("amount", 0) or 0), 2)
    if amount <= 0 or amount > due + 0.005:
        raise ValueError("El pago debe ser positivo y no exceder el saldo del folio")
    method = str(payload.get("method") or "").strip().lower()
    if not method:
        raise ValueError("method es requerido para una liquidación por pago")

    from src.app.modules.billing.schemas import PaymentCreate
    from src.app.modules.billing.service.lifecycle.payments import create_payment
    payment_reference = f"PAY-SETTLEMENT-{idempotency_key}"
    existing_payment = db.reservation_payments.find_one({
        "booking_id": booking_id,
        "reference": payment_reference,
    })
    payment = existing_payment
    if payment is None:
        payment = create_payment(
            PaymentCreate(
                booking_id=booking_id,
                amount=amount,
                method=method,
            ),
            reference=payment_reference,
            shift_id=shift_id,
            paid_at=effective_at,
            evidence_type=evidence_type,
            evidence_reference=evidence_reference,
            payment_source="historical_attestation" if effective_at else None,
            actor_user_id=actor_oid,
            actor_username=changed_by,
        )
    elif round(float(payment.get("amount", 0) or 0), 2) != amount or payment.get("status") != "confirmed":
        raise ValueError("La clave de idempotencia ya fue usada con un pago incompatible")
    if not payment or payment.get("status") != "confirmed":
        raise ValueError("No se pudo confirmar el pago y el saldo permanece abierto")

    refreshed = db[FOLIO_COLLECTION].find_one({"_id": folio["_id"]})
    if not refreshed:
        return None
    remaining = round(float(refreshed.get("total_due", 0) or 0), 2)
    final_status = "settled" if remaining <= 0.005 else "open"
    if final_status == "settled":
        refreshed = db[FOLIO_COLLECTION].find_one_and_update(
            {"_id": folio["_id"], "status": "open", "total_due": {"$lte": 0.005}},
            {"$set": {
                "status": "settled",
                "settlement_type": "payment",
                "settlement_amount": round(float(refreshed.get("total_payments", amount) or amount), 2),
                "settled_at": effective_at or now,
                "settled_recorded_at": now,
                "settled_by": changed_by,
                "settled_by_user_id": actor_oid,
                "settlement_evidence_type": evidence_type,
                "settlement_evidence_reference": evidence_reference,
                "updated_at": now,
            }},
            return_document=ReturnDocument.AFTER,
        ) or refreshed

    payment_id = payment.get("_id") or ObjectId(payment["id"])
    # Keep the operational payment and its fact mirror explicitly linked to
    # the folio. The posting reference is useful for reconciliation, but it is
    # not a stable foreign-key path for API consumers or audit screens.
    payment_trace_update = {
        "folio_id": folio["_id"],
        "folio_number": folio.get("folio_number", ""),
        "updated_at": now,
    }
    db.reservation_payments.update_one({"_id": payment_id}, {"$set": payment_trace_update})
    db.fact_reservation_payments.update_one({"_id": payment_id}, {"$set": payment_trace_update})
    payment.update(payment_trace_update)
    if effective_at is not None and method in {"cash", "efectivo"}:
        _link_settlement_payment_to_shift(
            db,
            shift_id=shift_id or "",
            payment=payment,
            booking_id=booking_id,
            folio_id=folio["_id"],
            effective_at=effective_at,
        )
    event = {
        "_id": ObjectId(),
        "booking_id": booking_id,
        "folio_id": folio["_id"],
        "prop_id": folio.get("prop_id", 0),
        "folio_number": folio.get("folio_number", ""),
        "settlement_type": "payment",
        "amount": amount,
        "payment_id": payment_id,
        "payment_reference": payment.get("reference"),
        "invoice_id": refreshed.get("invoice_id") or folio.get("invoice_id"),
        "shift_id": payment.get("shift_id") or _to_object_id_ref(shift_id),
        "idempotency_key": idempotency_key,
        "status": final_status,
        "effective_at": effective_at or payment.get("paid_at") or now,
        "evidence_type": evidence_type,
        "evidence_reference": evidence_reference,
        "changed_by": changed_by,
        "actor_user_id": actor_oid,
        "created_at": now,
    }
    try:
        _write_settlement_event(db, event)
    except Exception:
        if not db.folio_settlement_events.find_one({"booking_id": booking_id, "idempotency_key": idempotency_key}):
            raise
    trace_update = {
        "settlement_payment_id": payment_id,
        "settlement_event_id": event["_id"],
        "settlement_shift_id": event.get("shift_id"),
        "settlement_invoice_id": event.get("invoice_id"),
        "updated_at": now,
    }
    trace_update_operator = {"$set": trace_update, "$addToSet": {
        "settlement_event_ids": event["_id"],
        "settlement_payment_ids": payment_id,
    }}
    if event.get("shift_id"):
        trace_update_operator["$addToSet"]["settlement_shift_ids"] = event["shift_id"]
    db[FOLIO_COLLECTION].update_one({"_id": folio["_id"]}, trace_update_operator)
    db.reservation_payments.update_one({"_id": payment_id}, {"$set": {"settlement_event_id": event["_id"]}})
    db.fact_reservation_payments.update_one({"_id": payment_id}, {"$set": {"settlement_event_id": event["_id"]}})
    _record_settlement_audit(
        prop_id=int(folio.get("prop_id", 0) or 0),
        booking_id=booking_id,
        settlement_type="payment",
        amount=amount,
        changed_by=changed_by,
        idempotency_key=idempotency_key,
        effective_at=effective_at,
        evidence_reference=evidence_reference,
        actor_user_id=actor_oid,
    )
    return _enrich_folio(refreshed)


def close_folio(
    booking_id: str,
    invoice_id: str | ObjectId | None = None,
    closed_by: str = "system",
    close_reason: str | None = None,
) -> dict | None:
    """Close a folio at check-out after invoice and payment are settled.

    Sets status=closed, records the invoice_id, and stores the closing
    timestamp and user.
    """
    db = get_database()
    now = _now()

    # A closed folio is immutable. A positive balance may only be closed with
    # an explicit, auditable exception (write-off, complimentary stay, or
    # approved external settlement). Historical dirty folios remain closed and
    # are handled by reconciliation; this guard applies to new mutations.
    current = db[FOLIO_COLLECTION].find_one(
        {"booking_id": booking_id, "status": "open"},
        {"total_due": 1},
    )
    if current is None:
        return None
    balance = round(float(current.get("total_due", 0) or 0), 2)
    allowed_exception_reasons = {"approved_write_off", "complimentary_stay", "approved_external_settlement"}
    reason_code = (close_reason or "").strip().split(":", 1)[0].strip().lower()
    if balance > 0 and reason_code not in allowed_exception_reasons:
        return None

    # Canonical FK type: ``guest_folios.invoice_id`` references
    # ``reservation_invoices._id`` and must be stored as ObjectId (same
    # reference in ``reservation_payments.invoice_id`` is already ObjectId).
    # The checkout + API callers pass the hex string from ``str(inv["_id"])``;
    # normalize here so the DB never sees a mixed type (audit 2026-08).
    invoice_oid = _to_object_id_ref(invoice_id)

    result = db[FOLIO_COLLECTION].find_one_and_update(
        {"booking_id": booking_id, "status": "open"},
        {
            "$set": {
                "status": "closed",
                "closed_at": now,
                "closed_by": closed_by,
                "invoice_id": invoice_oid,
                "close_reason": close_reason.strip() if close_reason else None,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return _enrich_folio(result) if result else None


def reopen_folio_with_balance(
    booking_id: str,
    *,
    changed_by: str = "historical_reconciliation",
) -> dict | None:
    """Reopen a historically closed folio whose positive balance is collectible.

    This is an explicit reconciliation operation, not a second close path.
    It preserves the original close timestamp/user, records the reason in the
    folio metadata and emits one status-history event. Repeating the operation
    is a no-op once the folio is open, so retries cannot duplicate audit rows.
    """
    db = get_database()
    folio = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    if not folio:
        return None
    if folio.get("status") == "open":
        return _enrich_folio(folio)
    previous_status = str(folio.get("status") or "")
    if previous_status not in {"closed", "settled"} or round(float(folio.get("total_due", 0) or 0), 2) <= 0:
        return None

    now = _now()
    reconciliation = {
        "action": "reopened_collectible_balance",
        "reason": "settled_or_closed_folio_has_positive_balance",
        "previous_status": previous_status,
        "changed_by": changed_by,
        "changed_at": now,
    }
    result = db[FOLIO_COLLECTION].find_one_and_update(
        {
            "_id": folio["_id"],
            "status": {"$in": ["closed", "settled"]},
            "total_due": {"$gt": 0},
        },
        {"$set": {
            "status": "open",
            "reopened_at": now,
            "reopened_by": changed_by,
            "metadata.reconciliation": reconciliation,
            "updated_at": now,
        }},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        current = db[FOLIO_COLLECTION].find_one({"_id": folio["_id"]})
        return _enrich_folio(current) if current else None

    # The metadata action is the idempotency marker. Only the winner of the
    # closed→open CAS writes the operational history event.
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "folio_reopened_for_collection",
        "changed_at": now,
        "reason": "settled_or_closed_folio_has_positive_balance",
        "changed_by": changed_by,
        "is_test": False,
        "metadata": {"folio_id": str(folio["_id"])},
    })
    return _enrich_folio(result)


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
            {
                "booking_id": {"$in": expired_ids},
                "status": "open",
                "$or": [{"total_due": {"$lte": 0}}, {"total_due": {"$exists": False}}],
            },
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
    {"id": "early_checkin", "label": "Early Check-In", "icon": "alarm"},
    {"id": "no_show", "label": "No-Show", "icon": "event_busy"},
    {"id": "descuento", "label": "Descuento", "icon": "sell"},
    {"id": "otros", "label": "Otros", "icon": "more_horiz"},
]
