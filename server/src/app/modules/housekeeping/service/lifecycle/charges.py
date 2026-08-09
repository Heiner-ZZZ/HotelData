"""Additional charges operations."""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any

from pymongo import ReturnDocument

from src.database.connection import get_database
from ..collections import CHARGES_COLLECTION
from ...schemas import AdditionalChargeCreate, AdditionalChargeUpdate, now_iso


def _record_charge_posted_event(
    *,
    prop_id: int,
    booking_id: str,
    charge_id: str,
    total: float,
    trace: dict[str, Any],
    changed_by: str,
) -> dict[str, Any] | None:
    """Record the idempotent operations-side event after folio commit.

    The folio posting is the financial operation; this event is its durable
    integration evidence. Event failure must not relabel a committed charge as
    failed, so callers can expose the event status independently and retry it.
    """
    try:
        from src.app.modules.financial_reconciliation.domain_events import append_domain_event
        return append_domain_event(
            prop_id=int(prop_id),
            event_type="operations.additional_charge.posted",
            aggregate_type="operations",
            aggregate_id=charge_id,
            idempotency_key=f"additional-charge-posting:v1:{charge_id}",
            payload={
                "booking_id": booking_id,
                "charge_id": charge_id,
                "total": round(float(total), 2),
                "folio_id": str(trace.get("folio_id")) if trace.get("folio_id") else None,
                "folio_number": trace.get("folio_number"),
                "posting_id": str(trace.get("posting_id")) if trace.get("posting_id") else None,
                "posting_reference": trace.get("posting_reference"),
                "changed_by": changed_by,
            },
            source_collection=CHARGES_COLLECTION,
            source_id=charge_id,
            actor_id=changed_by,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to emit posted-charge event for %s", charge_id,
        )
        return None


def create_additional_charge(payload: AdditionalChargeCreate) -> dict[str, Any] | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id})
    if not booking:
        return None
    now = now_iso()
    charge_dt = payload.charge_date or now
    category = payload.category or _infer_category(payload.concept)
    total = round(payload.amount * max(1, payload.quantity), 2)
    doc = {
        "booking_id": payload.booking_id, "prop_id": payload.prop_id,
        "concept": payload.concept, "amount": round(payload.amount, 2),
        "quantity": max(1, payload.quantity),
        "total": total,
        "category": category,
        "note": payload.note, "created_at": now,
        "charge_date": charge_dt,
        "status": "active",
        "posting_status": "pending",
        "posting_error": None,
        "posting_reference": str(payload.booking_id),
        "posting_version": 1,
    }
    booking_prop_id = int(booking.get("prop_id", 0) or 0)
    if booking_prop_id != int(payload.prop_id):
        return None
    result = db[CHARGES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    # ── Auto-post to the guest folio ──
    try:
        from src.app.modules.billing.service.folio import get_folio_posting_trace, post_to_folio
        folio = post_to_folio(
            payload.booking_id,
            posting_type="charge",
            category=category,
            concept=payload.concept,
            amount=total,
            quantity=payload.quantity,
            reference_id=str(result.inserted_id),
            reference_type="additional_charge",
        )
        if folio is None:
            raise RuntimeError("guest folio not found")
        trace = get_folio_posting_trace(
            db,
            booking_id=payload.booking_id,
            reference_id=str(result.inserted_id),
            reference_type="additional_charge",
        )
        if not trace:
            raise RuntimeError("folio posting committed without trace")
        posted_update = {"posting_status": "posted", "posting_error": None}
        posted_update.update(trace)
        event = _record_charge_posted_event(
            prop_id=int(payload.prop_id),
            booking_id=payload.booking_id,
            charge_id=str(result.inserted_id),
            total=total,
            trace=trace,
            changed_by="charge_create",
        )
        if event:
            posted_update["domain_event_id"] = event.get("event_id")
            posted_update["domain_event_status"] = "posted"
        else:
            posted_update["domain_event_status"] = "failed"
        db[CHARGES_COLLECTION].update_one(
            {"_id": result.inserted_id},
            {"$set": posted_update},
        )
        doc.update(posted_update)
        try:
            from src.app.modules.billing.service import update_invoice_additional_charges
            update_invoice_additional_charges(
                payload.booking_id,
                changed_by="charge_create",
            )
        except Exception as exc:
            db[CHARGES_COLLECTION].update_one(
                {"_id": result.inserted_id},
                {"$set": {
                    "invoice_reconciliation_status": "failed",
                    "invoice_reconciliation_error": str(exc),
                }},
            )
            doc["invoice_reconciliation_status"] = "failed"
            doc["invoice_reconciliation_error"] = str(exc)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to auto-post charge to folio for booking %s", payload.booking_id
        )
        db[CHARGES_COLLECTION].update_one(
            {"_id": result.inserted_id},
            {"$set": {"posting_status": "posting_failed", "posting_error": str(exc)}},
        )
        doc["posting_status"] = "posting_failed"
        doc["posting_error"] = str(exc)

    return _enrich_charge(doc)


def repair_failed_charge(
    charge_id: str,
    *,
    changed_by: str = "historical_reconciliation",
) -> dict[str, Any] | None:
    """Attach a failed charge to a safe folio and post it exactly once.

    The booking and property are the safety boundary. If no folio exists, it
    is reconstructed from the booking's immutable sold amount; a positive
    balance is never silently written off. The charge ObjectId is the stable
    posting key, so retries converge without duplicate folio movements.
    """
    db = get_database()
    try:
        from bson import ObjectId
        charge_oid = ObjectId(charge_id)
    except Exception:
        return None

    charge = db[CHARGES_COLLECTION].find_one({"_id": charge_oid})
    if not charge or charge.get("status") == "reversed":
        return None
    booking_id = str(charge.get("booking_id") or "")
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if not booking or int(booking.get("prop_id", 0) or 0) != int(charge.get("prop_id", 0) or 0):
        return None

    from src.app.modules.billing.service.folio import (
        create_folio,
        post_to_folio,
        reopen_folio_with_balance,
    )

    folio = db.guest_folios.find_one({
        "booking_id": booking_id,
        "prop_id": int(charge.get("prop_id", 0) or 0),
    })
    if folio and folio.get("status") == "closed" and float(folio.get("total_due", 0) or 0) > 0:
        reopen_folio_with_balance(booking_id, changed_by=changed_by)
        folio = db.guest_folios.find_one({"_id": folio["_id"]})
    if not folio:
        # create_folio derives its room posting from booking.total_price and
        # refuses to invent a folio for an unknown booking.
        if create_folio(booking_id) is None:
            return None
        folio = db.guest_folios.find_one({"booking_id": booking_id})
    if not folio or folio.get("status") != "open":
        return None

    amount = round(float(charge.get("total", 0) or 0), 2)
    if amount <= 0:
        return None
    posted = post_to_folio(
        booking_id,
        posting_type="charge",
        category=charge.get("category", "otros"),
        concept=charge.get("concept", ""),
        amount=amount,
        quantity=int(charge.get("quantity", 1) or 1),
        reference_id=charge_id,
        reference_type="additional_charge",
    )
    if posted is None:
        return _enrich_charge(charge)

    from src.app.modules.billing.service.folio import get_folio_posting_trace
    trace = get_folio_posting_trace(
        db,
        booking_id=booking_id,
        reference_id=charge_id,
        reference_type="additional_charge",
    )
    if not trace:
        return _enrich_charge(charge)

    now = datetime.now(timezone.utc)
    event = _record_charge_posted_event(
        prop_id=int(charge.get("prop_id", 0) or 0),
        booking_id=booking_id,
        charge_id=charge_id,
        total=amount,
        trace=trace,
        changed_by=changed_by,
    )
    update = {
        "posting_status": "posted",
        "posting_error": None,
        **trace,
        "domain_event_id": event.get("event_id") if event else None,
        "domain_event_status": "posted" if event else "failed",
        "posting_repaired_at": now,
        "posting_repaired_by": changed_by,
        "metadata.reconciliation": {
            "action": "attached_failed_charge_to_folio",
            "charge_id": charge_id,
            "folio_id": str(folio["_id"]),
            "folio_number": folio.get("folio_number"),
            "changed_by": changed_by,
            "changed_at": now,
        },
        "updated_at": now,
    }
    # Legacy charges may not have a status field at all; absence is the
    # historical equivalent of active. Keep the CAS broad enough to repair
    # those documents without allowing an already-reversed charge through.
    db[CHARGES_COLLECTION].update_one(
        {"_id": charge_oid, "$or": [{"status": "active"}, {"status": {"$exists": False}}]},
        {"$set": update},
    )
    refreshed = db[CHARGES_COLLECTION].find_one({"_id": charge_oid})
    return _enrich_charge(refreshed) if refreshed else None


def update_additional_charge(charge_id: str, payload: AdditionalChargeUpdate) -> dict[str, Any] | None:
    """Update an additional charge. Only allowed if created on the same calendar day."""
    db = get_database()
    try:
        from bson import ObjectId
        obj_id = ObjectId(charge_id)
    except Exception:
        return None

    charge = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
    if not charge:
        return None

    if charge.get("status") == "reversed":
        return None
    if charge.get("posting_status") in {"updating", "reversing"}:
        # A concurrent edit/void owns the financial side effects. Do not
        # publish another reversal or replacement until that operation has
        # reconciled its version.
        return _enrich_charge(charge)
    db_folio = db.guest_folios.find_one({"booking_id": charge.get("booking_id", "")}, {"status": 1})
    if db_folio and db_folio.get("status") != "open":
        return None

    # ── Same-day validation ──
    created = charge.get("created_at")
    if created:
        if isinstance(created, datetime):
            created_dt = created.replace(tzinfo=timezone.utc) if created.tzinfo is None else created
        else:
            created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        if created_dt.date() != now_dt.date():
            return None  # not same calendar day → cannot edit

    # ── Build update ──
    update: dict[str, Any] = {}
    if payload.concept is not None:
        update["concept"] = payload.concept
    if payload.amount is not None:
        update["amount"] = round(payload.amount, 2)
    if payload.quantity is not None:
        update["quantity"] = max(1, payload.quantity)
    if payload.note is not None:
        update["note"] = payload.note
    if payload.charge_date is not None:
        update["charge_date"] = payload.charge_date

    if not update:
        return _enrich_charge(charge)  # nothing to update

    # Recalculate total if amount or quantity changed
    if "amount" in update or "quantity" in update:
        amt = update.get("amount", charge.get("amount", 0))
        qty = update.get("quantity", charge.get("quantity", 1))
        update["total"] = round(amt * qty, 2)

    # Claim this version before emitting any compensating postings. This is
    # the CAS boundary that prevents two concurrent edits from both reversing
    # the same source event.
    claimed = db[CHARGES_COLLECTION].find_one_and_update(
        {"_id": obj_id, "status": "active", "posting_status": {"$nin": ["updating", "reversing"]},
         "posting_version": int(charge.get("posting_version", 1) or 1)},
        {"$set": {"posting_status": "updating", "updated_at": now_iso()}},
        return_document=True,
    )
    if claimed is None:
        current = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
        return _enrich_charge(current) if current else None

    # ── Update folio: immutable reversal + versioned replacement ──
    try:
        from src.app.modules.billing.service.folio import get_folio_posting_trace, post_to_folio
        old_total = float(charge.get("total", 0) or 0)
        version = int(charge.get("posting_version", 1) or 1)
        old_posting = post_to_folio(
            charge.get("booking_id", ""),
            posting_type="charge_reversal",
            category=charge.get("category", "otros"),
            concept=f"[EDITADO] {charge.get('concept', '')}",
            amount=old_total,
            quantity=charge.get("quantity", 1),
            reference_id=f"{charge_id}:v{version}:reversal",
            reference_type="charge_edit_reversal",
        )
        if old_posting is None:
            raise RuntimeError("guest folio is unavailable for charge edit reversal")

        new_total = float(update.get("total", old_total) or 0)
        next_version = version + 1
        replacement = post_to_folio(
            charge.get("booking_id", ""),
            posting_type="charge",
            category=charge.get("category", "otros"),
            concept=update.get("concept", charge.get("concept", "")),
            amount=new_total,
            quantity=update.get("quantity", charge.get("quantity", 1)),
            reference_id=f"{charge_id}:v{next_version}",
            reference_type="additional_charge_revision",
        )
        if replacement is None:
            raise RuntimeError("guest folio is unavailable for charge replacement")
        update["posting_status"] = "posted"
        update["posting_error"] = None
        update["posting_version"] = next_version
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to update folio postings for charge %s", charge_id
        )
        update["posting_status"] = "posting_failed"
        update["posting_error"] = str(exc)

    if update.get("posting_status") == "posting_failed":
        # Do not expose a financial amount that the folio did not receive.
        # Keep the requested values in the retry payload for an operator.
        db[CHARGES_COLLECTION].update_one(
            {"_id": obj_id},
            {"$set": {
                "posting_status": "posting_failed",
                "posting_error": update.get("posting_error"),
                "pending_update": {
                    key: value for key, value in update.items()
                    if key in {"concept", "amount", "quantity", "total", "note", "charge_date"}
                },
                "updated_at": now_iso(),
            }},
        )
    else:
        # The replacement is committed; clear the transient CAS marker and
        # retain the new amount/version as the source-of-truth snapshot.
        db[CHARGES_COLLECTION].update_one({"_id": obj_id}, {"$set": update})

    # Reload enriched
    updated = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
    if updated and updated.get("posting_status") == "posted":
        try:
            from src.app.modules.billing.service import update_invoice_additional_charges
            update_invoice_additional_charges(
                str(updated.get("booking_id", "")),
                changed_by="charge_edit",
            )
        except Exception as exc:
            # Charge/folio remains valid; invoice reconciliation is explicitly
            # retryable and must not turn a successful charge edit into a
            # false failure response.
            db[CHARGES_COLLECTION].update_one(
                {"_id": obj_id},
                {"$set": {"invoice_reconciliation_status": "failed", "invoice_reconciliation_error": str(exc)}},
            )
            updated["invoice_reconciliation_status"] = "failed"
            updated["invoice_reconciliation_error"] = str(exc)
    return _enrich_charge(updated) if updated else None


def _infer_category(concept: str) -> str:
    """Infer charge category from concept text if not provided."""
    concept_lower = concept.lower()
    category_map = {
        "minibar": "minibar",
        "spa": "spa",
        "restaurante": "restaurante",
        "comida": "restaurante",
        "cena": "restaurante",
        "desayuno": "restaurante",
        "bar": "restaurante",
        "lavandería": "lavanderia",
        "lavanderia": "lavanderia",
        "parking": "parking",
        "estacionamiento": "parking",
        "mascota": "mascotas",
        "pet": "mascotas",
        "room service": "room_service",
        "habitación": "room_service",
        "daño": "danos",
        "daños": "danos",
        "damage": "danos",
        "late checkout": "late_checkout",
        "salida tarde": "late_checkout",
        "amenidad": "amenities",
    }
    for keyword, cat in category_map.items():
        if keyword in concept_lower:
            return cat
    return "otros"


def list_additional_charges(
    booking_id: str | None = None, prop_id: int | None = None,
    page: int = 1, page_size: int = 20,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {}
    if booking_id:
        query["booking_id"] = booking_id
    if prop_id:
        query["prop_id"] = prop_id
    total = db[CHARGES_COLLECTION].count_documents(query)
    cursor = db[CHARGES_COLLECTION].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_charge(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def recover_additional_charge(
    charge_id: str,
    *,
    db: Any | None = None,
) -> dict[str, Any] | None:
    """Finish a charge mutation interrupted after its folio side effect.

    Recovery is deliberately conservative: it only finalizes a ``reversing``
    charge when the stable reversal posting already exists. It never invents
    a new amount or silently retries an unknown partial edit.
    """
    db = db if db is not None else get_database()
    try:
        from bson import ObjectId
        obj_id = ObjectId(charge_id)
    except Exception:
        return None
    charge = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
    if not charge:
        return None

    status = charge.get("posting_status")
    version = int(charge.get("posting_version", 1) or 1)
    booking_id = str(charge.get("booking_id", ""))
    if status == "reversing":
        reversal_ref = f"{charge_id}:v{version}:reversal"
        posted = db.guest_folios.find_one({
            "booking_id": booking_id,
            "postings": {"$elemMatch": {
                "reference_id": reversal_ref,
                "reference_type": "charge_reversal",
            }},
        }, {"_id": 1})
        if not posted:
            return _enrich_charge(charge)
        updated = db[CHARGES_COLLECTION].find_one_and_update(
            {"_id": obj_id, "status": "active", "posting_status": "reversing"},
            {"$set": {
                "status": "reversed",
                "posting_status": "reversed",
                "posting_error": None,
                "reversed_at": now_iso(),
                "updated_at": now_iso(),
            }},
            return_document=ReturnDocument.AFTER,
        )
        final = updated or charge
        if updated:
            try:
                from src.app.modules.billing.service import update_invoice_additional_charges
                update_invoice_additional_charges(booking_id, changed_by="charge_recovery")
            except Exception as exc:
                db[CHARGES_COLLECTION].update_one(
                    {"_id": obj_id},
                    {"$set": {
                        "invoice_reconciliation_status": "failed",
                        "invoice_reconciliation_error": str(exc),
                    }},
                )
                final["invoice_reconciliation_status"] = "failed"
                final["invoice_reconciliation_error"] = str(exc)
        return _enrich_charge(final)

    if status == "updating":
        pending = charge.get("pending_update") or {}
        version_ref = f"{charge_id}:v{version + 1}"
        replacement = db.guest_folios.find_one({
            "booking_id": booking_id,
            "postings": {"$elemMatch": {
                "reference_id": version_ref,
                "reference_type": "additional_charge_revision",
            }},
        }, {"_id": 1})
        reversal = db.guest_folios.find_one({
            "booking_id": booking_id,
            "postings": {"$elemMatch": {
                "reference_id": f"{charge_id}:v{version}:reversal",
                "reference_type": "charge_edit_reversal",
            }},
        }, {"_id": 1})
        # A replacement without the compensating reversal would duplicate the
        # charge in the folio. Leave the source in ``updating`` until both
        # immutable events exist; the operator/worker can retry recovery later.
        if not replacement or not reversal or not pending:
            return _enrich_charge(charge)

        updated = db[CHARGES_COLLECTION].find_one_and_update(
            {"_id": obj_id, "status": "active", "posting_status": "updating"},
            {"$set": {
                **pending,
                "posting_status": "posted",
                "posting_error": None,
                "posting_version": version + 1,
                "pending_update": None,
                "updated_at": now_iso(),
            }},
            return_document=ReturnDocument.AFTER,
        )
        final = updated or charge
        if updated:
            try:
                from src.app.modules.billing.service import update_invoice_additional_charges
                update_invoice_additional_charges(booking_id, changed_by="charge_recovery")
            except Exception as exc:
                db[CHARGES_COLLECTION].update_one(
                    {"_id": obj_id},
                    {"$set": {
                        "invoice_reconciliation_status": "failed",
                        "invoice_reconciliation_error": str(exc),
                    }},
                )
                final["invoice_reconciliation_status"] = "failed"
                final["invoice_reconciliation_error"] = str(exc)
        return _enrich_charge(final)

    return _enrich_charge(charge)


def delete_additional_charge(charge_id: str) -> dict | None:
    """Void a charge without deleting its financial evidence.

    A charge may already be present in an issued/closed folio. Physical
    deletion would make the folio and invoice impossible to audit, so the
    source document is retained and a single compensating folio event is
    appended. Repeating the request returns the already-reversed document.
    """
    db = get_database()
    try:
        from bson import ObjectId
        obj_id = ObjectId(charge_id)
    except Exception:
        return None

    charge = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
    if not charge:
        return None
    if charge.get("posting_status") in {"updating", "reversing"}:
        # The route translates this to a conflict; never claim the void
        # succeeded while another financial mutation owns the charge.
        return None
    if charge.get("status") == "reversed":
        return _enrich_charge(charge)

    # Claim the source document before posting the compensating event. A
    # second concurrent void now observes ``reversing`` and cannot append a
    # duplicate reversal to the folio.
    claimed = db[CHARGES_COLLECTION].find_one_and_update(
        {"_id": obj_id, "status": "active", "posting_status": {"$nin": ["updating", "reversing"]}},
        {"$set": {"posting_status": "reversing", "updated_at": now_iso()}},
        return_document=True,
    )
    if claimed is None:
        current = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
        if current and current.get("status") == "reversed":
            return _enrich_charge(current)
        return None
    charge = claimed

    amount = abs(float(charge.get("total", 0) or 0))
    try:
        from src.app.modules.billing.service.folio import get_folio_posting_trace, post_to_folio
        folio = post_to_folio(
            charge.get("booking_id", ""),
            posting_type="charge_reversal",
            category=charge.get("category", "otros"),
            concept=f"[ANULADO] {charge.get('concept', '')}",
            amount=amount,
            quantity=charge.get("quantity", 1),
            reference_id=f"{charge_id}:v{int(charge.get('posting_version', 1) or 1)}:reversal",
            reference_type="charge_reversal",
        )
        if folio is None:
            raise RuntimeError("guest folio is unavailable for charge reversal")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to reverse folio posting for charge %s", charge_id
        )
        db[CHARGES_COLLECTION].update_one(
            {"_id": obj_id, "status": {"$ne": "reversed"}},
            {"$set": {
                "posting_status": "reversal_failed",
                "posting_error": str(exc),
                "updated_at": now_iso(),
            }},
        )
        return None

    updated = db[CHARGES_COLLECTION].find_one_and_update(
        {"_id": obj_id, "status": {"$ne": "reversed"}, "posting_status": "reversing"},
        {"$set": {
            "status": "reversed",
            "posting_status": "reversed",
            "posting_error": None,
            "reversed_at": now_iso(),
            "updated_at": now_iso(),
        }},
        return_document=True,
    )
    final = updated or charge
    if updated:
        try:
            from src.app.modules.billing.service import update_invoice_additional_charges
            update_invoice_additional_charges(
                str(final.get("booking_id", "")),
                changed_by="charge_void",
            )
        except Exception as exc:
            db[CHARGES_COLLECTION].update_one(
                {"_id": obj_id},
                {"$set": {"invoice_reconciliation_status": "failed", "invoice_reconciliation_error": str(exc)}},
            )
            final["invoice_reconciliation_status"] = "failed"
            final["invoice_reconciliation_error"] = str(exc)
    return _enrich_charge(final)


def _enrich_charge(doc: dict) -> dict:
    """Normalize charge doc for API responses.

    Adds camelCase aliases for fields the frontend reads (bookingId,
    propId, createdAt, chargeDate) while keeping the original snake_case
    keys intact so existing API consumers (e.g. instay handlers) are not
    broken.
    """
    doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc:
        formatted = _fmt(doc["created_at"])
        doc["created_at"] = formatted
        doc["createdAt"] = formatted  # camelCase alias for frontend
    if "charge_date" in doc:
        formatted = _fmt(doc["charge_date"])
        doc["charge_date"] = formatted
        doc["chargeDate"] = formatted  # camelCase alias for frontend
    if "booking_id" in doc:
        doc["bookingId"] = str(doc["booking_id"])  # camelCase alias for frontend
    if "prop_id" in doc:
        doc["propId"] = doc["prop_id"]  # camelCase alias for frontend
    if "posting_status" in doc:
        doc["postingStatus"] = doc["posting_status"]
    if "posting_error" in doc:
        doc["postingError"] = doc["posting_error"]
    if "posting_id" in doc:
        doc["posting_id"] = str(doc["posting_id"]) if doc["posting_id"] else None
        doc["postingId"] = doc["posting_id"]
    if "posting_reference" in doc:
        doc["postingReference"] = str(doc["posting_reference"]) if doc["posting_reference"] else None
    if "posting_reference_type" in doc:
        doc["postingReferenceType"] = doc["posting_reference_type"]
    if "domain_event_id" in doc:
        doc["domainEventId"] = doc["domain_event_id"]
    if "domain_event_status" in doc:
        doc["domainEventStatus"] = doc["domain_event_status"]
    if "folio_id" in doc:
        doc["folio_id"] = str(doc["folio_id"]) if doc["folio_id"] else None
        doc["folioId"] = doc["folio_id"]
    if "folio_number" in doc:
        doc["folioNumber"] = doc["folio_number"]
    if "invoice_reconciliation_status" in doc:
        doc["invoiceReconciliationStatus"] = doc["invoice_reconciliation_status"]
    if "invoice_reconciliation_error" in doc:
        doc["invoiceReconciliationError"] = doc["invoice_reconciliation_error"]
    if "reversed_at" in doc:
        doc["reversedAt"] = _fmt(doc["reversed_at"])
    return doc


def get_additional_charge(charge_id: str) -> dict[str, Any] | None:
    """Retrieve a single additional charge by its ObjectId.

    Returns the enriched charge dict, or None if the charge does not
    exist or the supplied id is not a valid ObjectId.
    """
    db = get_database()
    try:
        from bson import ObjectId
        obj_id = ObjectId(charge_id)
    except Exception:
        return None
    doc = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
    if not doc:
        return None
    return _enrich_charge(doc)


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
