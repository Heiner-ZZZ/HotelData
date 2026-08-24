from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from src.app.core.timezone import local_now, local_today
from src.app.modules.partner.services.audit import register_action
from src.app.modules.reservations.notifications import notify_guest_status_change
from src.database.connection import get_database

from ._helpers import utc_now

logger = logging.getLogger(__name__)


def auto_cancel_expired_pending() -> dict[str, Any]:
    """Cancel all pending bookings older than 24 hours.

    Returns a summary dict with counts of cancelled bookings and any errors.
    """
    db = get_database()
    cutoff = utc_now() - timedelta(hours=24)
    cutoff_str = cutoff.isoformat()

    expired = list(
        db.booking_orders.find(
            {"status": "pending", "created_at": {"$lt": cutoff_str}},
            {"_id": 0, "booking_id": 1, "guest_name": 1, "guest_email": 1, "is_test": 1,
             "prop_id": 1, "check_in_date": 1, "check_out_date": 1, "total_price": 1,
             "currency": 1, "total_nights": 1, "created_at": 1},
        )
    )

    if not expired:
        logger.info("auto_cancel_expired_pending: no expired pending bookings found")
        return {"cancelled": 0, "errors": [], "expired_count": 0}

    cancelled = 0
    errors: list[str] = []
    for booking in expired:
        booking_id = booking["booking_id"]
        try:
            cancel_booking(
                booking_id,
                reason="auto_cancel_24h",
                changed_by="auto_cancel_scheduler",
            )
            cancelled += 1
            logger.info("Auto-cancelled expired booking %s (created: %s)", booking_id, booking.get("created_at"))
        except Exception as exc:
            err_msg = f"{booking_id}: {exc}"
            errors.append(err_msg)
            logger.exception("Failed to auto-cancel booking %s", booking_id)

    # Log execution to etl_executions
    try:
        db.etl_executions.insert_one({
            "execution_id": f"AUTO_CANCEL_{utc_now().strftime('%Y%m%d%H%M%S')}",
            "executed_at": utc_now(),
            "pipeline": "auto_cancel_pending",
            "status": "completed" if not errors else "completed_with_errors",
            "summary": {
                "expired_found": len(expired),
                "cancelled": cancelled,
                "errors": len(errors),
            },
        })
    except Exception:
        logger.exception("Failed to log auto_cancel execution")

    return {
        "cancelled": cancelled,
        "errors": errors,
        "expired_count": len(expired),
    }


def room_rate_per_night(booking: dict) -> float:
    """Calculate the room rate per night from a booking document."""
    total_price = float(booking.get("total_price", 0) or 0)
    total_nights = int(booking.get("total_nights", 1)) or 1
    return round(total_price / total_nights, 2)


def resolve_penalty_percent(
    prop_id: int,
    room_type_id: str = "",
    rate_plan_id: str = "",
) -> int:
    """Read cancellation_penalty_percent from hotel_policies.

    Hierarchy: rate_plan > room_type > hotel-wide.
    Returns the configured percentage (0-100), defaulting to 100
    if no policy is found (full penalty).
    """
    db = get_database()
    policy = None
    if rate_plan_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "rate_plan_id": rate_plan_id},
            {"_id": 0, "cancellation_penalty_percent": 1},
        )
    if not policy and room_type_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_penalty_percent": 1},
        )
    if not policy:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_penalty_percent": 1},
        )
    if not policy:
        return 100
    return int(policy.get("cancellation_penalty_percent", 100) or 100)


def _calculate_cancellation_penalty(
    prop_id: int,
    check_in_date: str,
    total_price: float | None,
    total_nights: int,
    room_type_id: str = "",
    rate_plan_id: str = "",
) -> dict[str, Any]:
    """Determine if a cancellation penalty applies based on hotel policy.

    Checks rate-plan-specific policies first, then room-type, then hotel-wide.

    Returns a dict with:
      - free_cancellation: bool
      - penalty_percent: int
      - penalty_amount: float
      - hours_until_checkin: int | None
      - cancellation_hours: int
    """
    if not check_in_date:
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": 0}

    db = get_database()
    # Hierarchy: rate_plan > room_type > hotel-wide
    policy = None
    # 1. Rate-plan-specific policy
    if rate_plan_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "rate_plan_id": rate_plan_id},
            {"_id": 0, "cancellation_hours": 1, "cancellation_penalty_percent": 1},
        )
    # 2. Room-type-specific policy
    if not policy and room_type_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_hours": 1, "cancellation_penalty_percent": 1},
        )
    # 3. Hotel-wide fallback
    if not policy:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "cancellation_hours": 1, "cancellation_penalty_percent": 1},
        )
    if not policy:
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": 0}

    cancellation_hours = int(policy.get("cancellation_hours", 0) or 0)
    penalty_percent = int(policy.get("cancellation_penalty_percent", 100) or 100)

    if cancellation_hours <= 0:
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": 0}

    try:
        checkin_dt = datetime.fromisoformat(f"{check_in_date}T00:00:00+00:00")
    except (ValueError, TypeError):
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": None, "cancellation_hours": cancellation_hours}

    now = local_now()
    # check_in_date is at midnight, so hours_until = (checkin - now) total hours
    delta = checkin_dt - now
    hours_until_checkin = max(0, int(delta.total_seconds() / 3600))

    if hours_until_checkin >= cancellation_hours:
        # Outside penalty window → free cancellation
        return {"free_cancellation": True, "penalty_percent": 0, "penalty_amount": 0.0,
                "hours_until_checkin": hours_until_checkin, "cancellation_hours": cancellation_hours}

    # Inside penalty window → calculate amount
    if total_price is None or total_price <= 0 or total_nights <= 0:
        penalty_amount = 0.0
    else:
        one_night = total_price / total_nights
        penalty_amount = round(one_night * penalty_percent / 100, 2)

    # If penalty rounds to zero (or there's nothing to charge), treat as free cancellation
    if penalty_amount <= 0:
        return {
            "free_cancellation": True,
            "penalty_percent": 0,
            "penalty_amount": 0.0,
            "hours_until_checkin": hours_until_checkin,
            "cancellation_hours": cancellation_hours,
        }

    return {
        "free_cancellation": False,
        "penalty_percent": penalty_percent,
        "penalty_amount": penalty_amount,
        "hours_until_checkin": hours_until_checkin,
        "cancellation_hours": cancellation_hours,
    }


def cancel_booking(booking_id: str, *, reason: str = "cancelled_by_user", changed_by: str = "web") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise ValueError("No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.")
    if booking.get("status") != "pending":
        raise ValueError(
            "Solo se pueden cancelar reservas pendientes; esta reserva está en estado "
            f"'{booking.get('status', '')}'. Contactá a recepción para gestionar la cancelación."
        )
    today_str = local_today()
    if today_str >= booking.get("check_in_date", ""):
        raise ValueError("No se puede cancelar una reserva cuya fecha de entrada ya ha comenzado o pasado.")

    # ── Calculate cancellation penalty ──
    penalty = _calculate_cancellation_penalty(
        prop_id=int(booking.get("prop_id", 0)),
        check_in_date=booking.get("check_in_date", ""),
        total_price=booking.get("total_price"),
        total_nights=int(booking.get("total_nights", 0)),
        room_type_id=booking.get("room_type_id", ""),
        rate_plan_id=booking.get("rate_plan_id", ""),
    )

    changed_at = utc_now()
    update_set: dict[str, Any] = {
        "status": "cancelled",
        "updated_at": changed_at,
        "cancel_reason": reason,
        "cancellation_free": penalty["free_cancellation"],
        "cancellation_penalty_percent": penalty["penalty_percent"],
        "cancellation_penalty_amount": penalty["penalty_amount"],
    }
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": update_set},
    )

    reason_detail = reason
    if not penalty["free_cancellation"]:
        reason_detail = f"{reason} — penalización: ${penalty['penalty_amount']:.2f} ({penalty['penalty_percent']}% de 1 noche)"

    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "cancelled",
            "changed_at": changed_at,
            "reason": reason_detail,
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
            "cancellation_penalty_amount": penalty["penalty_amount"],
            "cancellation_free": penalty["free_cancellation"],
        }
    )

    # ── Audit log (universal) ──
    if booking and not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="cancel",
                summary=f"Reserva cancelada — {booking.get('guest_name', '')} — {penalty['penalty_amount']:.2f} USD penalización",
                changed_by=changed_by,
                metadata={"guest_name": booking.get("guest_name", ""), "reason": reason,
                         "free_cancellation": penalty["free_cancellation"],
                         "penalty_amount": penalty["penalty_amount"],
                         "penalty_percent": penalty["penalty_percent"]},
            )
        except Exception:
            logger.exception("Failed to register audit action for cancel %s", booking_id)
    if db.manual_reservations.count_documents({"booking_id": booking_id}) > 0:
        db.manual_reservations.update_one(
            {"booking_id": booking_id},
            {"$set": {"status": "cancelled", "updated_at": changed_at}},
        )

    # La estadía no ocurrió: anular la factura emitida al confirmar (si no
    # tiene pagos). La penalización queda registrada en el booking; la factura
    # no debe seguir mostrándose como "pendiente de pago".
    try:
        from src.app.modules.billing.service.lifecycle.invoices import cancel_stay_invoice_for_no_stay
        cancel_stay_invoice_for_no_stay(
            booking_id,
            reason=(
                f"Cancelación — penalización ${penalty['penalty_amount']:.2f} "
                f"({penalty['penalty_percent']}% de 1 noche) — la estadía no se factura."
            ),
            cancelled_by=changed_by,
        )
    except Exception:
        logger.exception("Failed to cancel stay invoice for cancellation %s", booking_id)

    # ── Register transaction on active shift ──
    if not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="cancellation",
                booking_id=booking_id,
                amount=-float(penalty["penalty_amount"]),
                description=f"Cancelación: {booking.get('guest_name', '')} — razón: {reason}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for cancellation %s", booking_id)

    # ── Notify guest on cancellation ──
    try:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=guest_email,
                new_status="cancelled",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=booking.get("check_in_date", ""),
                check_out_date=booking.get("check_out_date", ""),
                total_price=booking.get("total_price"),
                currency=booking.get("currency", "USD"),
                total_nights=int(booking.get("total_nights", 0)),
                reason=reason_detail,
            )
    except Exception:
        logger.exception("Failed to notify guest on cancel for booking %s", booking_id)

    return {
        "booking_id": booking_id,
        "status": "cancelled",
        "free_cancellation": penalty["free_cancellation"],
        "penalty_amount": penalty["penalty_amount"],
        "penalty_percent": penalty["penalty_percent"],
        "hours_until_checkin": penalty["hours_until_checkin"],
        "cancellation_hours": penalty["cancellation_hours"],
    }


def _cleanup_object_id(value: Any) -> ObjectId | None:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError, ValueError):
        return None


def _cleanup_values(*values: Any) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value is None or value == "":
            continue
        result.extend([value, str(value)])
        object_id = _cleanup_object_id(value)
        if object_id is not None:
            result.append(object_id)
    return list(dict.fromkeys(result))


def _cleanup_or(*clauses: dict[str, Any]) -> dict[str, Any]:
    return {"$or": list(clauses)} if clauses else {"_id": {"$in": []}}


def _cleanup_ids(db: Any, collection_name: str, query: dict[str, Any]) -> list[Any]:
    return [doc["_id"] for doc in db[collection_name].find(query, {"_id": 1})]


def cleanup_test_booking(booking_id: str) -> dict[str, Any]:
    """Remove a test booking's complete cross-module aggregate.

    The reservation flag is the safety gate. Once it is true, collect every
    direct foreign key (folio, invoice, payment and settlement ids) before a
    single Mongo transaction deletes operational/fact projections and their
    derived audit/outbox records. Reception shifts are shared aggregates: only
    this booking's embedded ids and transactions are removed, never the shift.
    """
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        return {"booking_id": booking_id, "deleted": False, "reason": "not_found"}
    if not booking.get("is_test"):
        return {"booking_id": booking_id, "deleted": False, "reason": "not_marked_as_test"}

    booking_object_id = booking.get("_id")
    booking_values = _cleanup_values(booking_id, booking_object_id)

    folio_query = {"booking_id": booking_id}
    folio_docs = list(db.guest_folios.find(folio_query))
    folio_ids = [doc["_id"] for doc in folio_docs]
    folio_numbers = [doc.get("folio_number") for doc in folio_docs if doc.get("folio_number")]
    folio_values = _cleanup_values(*folio_ids, *folio_numbers)
    posting_ids = [
        posting.get("posting_id")
        for folio in folio_docs
        for posting in (folio.get("postings") or [])
        if posting.get("posting_id")
    ]

    invoice_query = {"booking_id": booking_id}
    invoice_docs = list(db.reservation_invoices.find(invoice_query))
    invoice_ids = [doc["_id"] for doc in invoice_docs]
    invoice_numbers = [doc.get("invoice_number") for doc in invoice_docs if doc.get("invoice_number")]
    invoice_values = _cleanup_values(*invoice_ids, *invoice_numbers)

    payment_query = _cleanup_or(
        {"booking_id": booking_id},
        {"invoice_id": {"$in": invoice_values}},
    )
    payment_docs = list(db.reservation_payments.find(payment_query))
    payment_ids = [doc["_id"] for doc in payment_docs]
    payment_values = _cleanup_values(*payment_ids)

    settlement_query = _cleanup_or(
        {"booking_id": booking_id},
        {"folio_id": {"$in": folio_values}},
        {"invoice_id": {"$in": invoice_values}},
        {"payment_id": {"$in": payment_values}},
    )
    settlement_docs = list(db.folio_settlement_events.find(settlement_query))
    settlement_ids = [doc["_id"] for doc in settlement_docs]
    settlement_values = _cleanup_values(*settlement_ids)

    refund_query = _cleanup_or(
        {"payment_id": {"$in": payment_values}},
        {"invoice_id": {"$in": invoice_values}},
    )

    event_values = _cleanup_values(
        booking_id,
        booking_object_id,
        *folio_ids,
        *folio_numbers,
        *invoice_ids,
        *invoice_numbers,
        *payment_ids,
        *settlement_ids,
    )

    booking_id_collections = (
        "booking_guests",
        "booking_room_guests",
        "booking_status_history",
        "manual_reservations",
        "additional_charges",
        "notification_log",
        "housekeeping_tasks",
        "room_status_history",
        "room_status_log",
        "stay_sessions",
        "stay_service_requests",
        "stay_messages",
        "maintenance_tasks",
        "payment_reconciliation_events",
        "fact_hotel_reservations",
        "fact_hotel_events",
        "platform_earnings",
    )
    ids_by_collection: dict[str, list[Any]] = {
        collection_name: _cleanup_ids(db, collection_name, {"booking_id": booking_id})
        for collection_name in booking_id_collections
        if collection_name in db.list_collection_names()
    }

    ids_by_collection["booking_orders"] = [booking["_id"]]
    ids_by_collection["additional_charges"] = _cleanup_ids(
        db,
        "additional_charges",
        _cleanup_or({"booking_id": booking_id}, {"folio_id": {"$in": folio_values}}),
    )
    ids_by_collection["notification_log"] = _cleanup_ids(
        db,
        "notification_log",
        _cleanup_or({"booking_id": booking_id}, {"entity_id": {"$in": event_values}}),
    )
    ids_by_collection["payment_reconciliation_events"] = _cleanup_ids(
        db,
        "payment_reconciliation_events",
        _cleanup_or(
            {"booking_id": booking_id},
            {"payment_id": {"$in": payment_values}},
            {"invoice_id": {"$in": invoice_values}},
        ),
    )
    ids_by_collection["guest_folios"] = _cleanup_ids(
        db,
        "guest_folios",
        _cleanup_or({"booking_id": booking_id}, {"_id": {"$in": folio_values}}),
    )

    invoice_query_all = _cleanup_or(
        {"booking_id": booking_id},
        {"_id": {"$in": invoice_values}},
        {"invoice_number": {"$in": invoice_values}},
    )
    for collection_name in ("reservation_invoices", "fact_reservation_invoices"):
        ids_by_collection[collection_name] = _cleanup_ids(db, collection_name, invoice_query_all)

    payment_query_all = _cleanup_or(
        {"booking_id": booking_id},
        {"_id": {"$in": payment_values}},
        {"invoice_id": {"$in": invoice_values}},
    )
    for collection_name in ("reservation_payments", "fact_reservation_payments"):
        ids_by_collection[collection_name] = _cleanup_ids(db, collection_name, payment_query_all)

    for collection_name in ("folio_settlement_events", "fact_folio_settlement_events"):
        ids_by_collection[collection_name] = _cleanup_ids(db, collection_name, settlement_query)

    for collection_name in ("refund_documents", "fact_refund_documents"):
        if collection_name in db.list_collection_names():
            ids_by_collection[collection_name] = _cleanup_ids(db, collection_name, refund_query)

    ledger_query = _cleanup_or(
        {"booking_id": booking_id},
        {"source_id": {"$in": _cleanup_values(*invoice_numbers, *posting_ids, *folio_numbers)}},
        {"folio_ref": {"$in": folio_values}},
    )
    ids_by_collection["ledger_transactions"] = _cleanup_ids(db, "ledger_transactions", ledger_query)

    event_regex = {"$regex": "|".join(re.escape(str(value)) for value in event_values)}
    event_query = _cleanup_or(
        {"booking_id": booking_id},
        {"source_id": {"$in": event_values}},
        {"aggregate_id": {"$in": event_values}},
        {"payload.booking_id": booking_id},
        {"payload.folio_id": {"$in": folio_values}},
        {"idempotency_key": event_regex},
    )
    for collection_name in ("hotel_domain_events", "fact_hotel_domain_events"):
        ids_by_collection[collection_name] = _cleanup_ids(db, collection_name, event_query)

    text_values = [booking_id, *folio_numbers, *invoice_numbers]
    text_regex = {"$regex": "|".join(re.escape(str(value)) for value in text_values)}
    audit_query = _cleanup_or(
        {"entity_id": {"$in": event_values}},
        {"metadata.booking_id": booking_id},
        {"metadata.folio_number": {"$in": folio_values}},
        {"metadata.invoice_number": {"$in": invoice_values}},
        {"summary": text_regex},
        {"metadata.path": text_regex},
    )
    ids_by_collection["audit_log"] = _cleanup_ids(db, "audit_log", audit_query)

    outbox_query = _cleanup_or(
        {"document_id": {"$in": event_values}},
        {"operational_id": {"$in": event_values}},
        {"document._id": {"$in": event_values}},
        {"document.booking_id": booking_id},
        {"document.folio_id": {"$in": folio_values}},
        {"document.folio_number": {"$in": folio_values}},
        {"document.invoice_id": {"$in": invoice_values}},
        {"document.invoice_number": {"$in": invoice_values}},
        {"document.payment_id": {"$in": payment_values}},
        {"document.entity_id": {"$in": event_values}},
        {"document.payload.booking_id": booking_id},
        {"document.summary": text_regex},
        {"document.metadata.path": text_regex},
    )
    ids_by_collection["outbox"] = _cleanup_ids(db, "outbox", outbox_query)

    shift_query = _cleanup_or(
        {"booking_ids": {"$in": booking_values}},
        {"folio_ids": {"$in": folio_values}},
        {"transactions.booking_id": booking_id},
    )
    shift_ids = _cleanup_ids(db, "reception_shifts", shift_query)

    deleted: dict[str, int] = {}
    with db.client.start_session() as session, session.start_transaction():
        for collection_name, ids in ids_by_collection.items():
            if not ids:
                continue
            result = db[collection_name].delete_many({"_id": {"$in": ids}}, session=session)
            deleted[collection_name] = result.deleted_count

        shift_updated = 0
        for shift_id in shift_ids:
            shift_doc = db.reception_shifts.find_one({"_id": shift_id}, session=session)
            if not shift_doc:
                continue
            update_set: dict[str, Any] = {}
            if "booking_ids" in shift_doc:
                update_set["booking_ids"] = [
                    value for value in shift_doc["booking_ids"] if value not in booking_values
                ]
            if "folio_ids" in shift_doc:
                update_set["folio_ids"] = [
                    value for value in shift_doc["folio_ids"] if value not in folio_values
                ]
            if "transactions" in shift_doc:
                update_set["transactions"] = [
                    transaction for transaction in shift_doc["transactions"]
                    if not _cleanup_transaction_matches(
                        transaction,
                        booking_values,
                        folio_values,
                        invoice_values,
                        payment_values,
                    )
                ]
            if update_set:
                result = db.reception_shifts.update_one(
                    {"_id": shift_id},
                    {"$set": update_set},
                    session=session,
                )
                shift_updated += result.modified_count
        if shift_updated:
            deleted["reception_shifts"] = shift_updated

    return {"booking_id": booking_id, "deleted": True, "counts": deleted}


def _cleanup_transaction_matches(
    transaction: dict[str, Any],
    booking_values: list[Any],
    folio_values: list[Any],
    invoice_values: list[Any],
    payment_values: list[Any],
) -> bool:
    values = {
        str(value)
        for value in (
            transaction.get("booking_id"),
            transaction.get("folio_id"),
            transaction.get("invoice_id"),
            transaction.get("payment_id"),
        )
        if value is not None
    }
    target_values = {
        str(value)
        for value in (*booking_values, *folio_values, *invoice_values, *payment_values)
    }
    return bool(values & target_values)
