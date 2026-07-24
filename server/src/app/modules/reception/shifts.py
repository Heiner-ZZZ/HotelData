from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.app.core.resolvers import resolve_hotel_id, resolve_employee_id

from .collections import RECEPTION_SHIFTS_COLLECTION
from src.database.connection import get_database

logger = logging.getLogger(__name__)

SHIFT_TYPES = ("morning", "afternoon", "evening")

SHIFT_TYPE_LABELS = {
    "morning": "Matutino (08:00-16:00)",
    "afternoon": "Vespertino (16:00-00:00)",
    "evening": "Nocturno (00:00-08:00)",
}

DEFAULT_SHIFT_HOURS = {
    "morning": {"start": "08:00", "end": "16:00"},
    "afternoon": {"start": "16:00", "end": "00:00"},
    "evening": {"start": "00:00", "end": "08:00"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _generate_txn_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    token = secrets.token_hex(2).upper()
    return f"TXN-{stamp}-{token}"


def _enrich_shift(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if "transactions" in doc and isinstance(doc["transactions"], list):
        for txn in doc["transactions"]:
            for f in ("timestamp",):
                if f in txn and hasattr(txn[f], "isoformat"):
                    txn[f] = txn[f].isoformat()
    for f in ("start_time", "end_time", "closed_at"):
        if f in doc and hasattr(doc[f], "isoformat"):
            doc[f] = doc[f].isoformat()
    return doc


def _get_last_closed_shift(prop_id: int) -> dict | None:
    """Return the most recent closed shift for a property, or None."""
    db = get_database()
    return db[RECEPTION_SHIFTS_COLLECTION].find_one(
        {"prop_id": prop_id, "status": "closed"},
        sort=[("closed_at", -1)],
    )


def _collect_related_ids(prop_id: int, start: datetime, end: datetime) -> dict[str, list[ObjectId]]:
    """Collect ObjectId references to payments, folios and bookings created
    during the shift window.

    Payments are matched by ``paid_at``; folios and bookings by ``created_at``.
    """
    db = get_database()

    payment_ids = [
        doc["_id"]
        for doc in db.reservation_payments.find(
            {"prop_id": prop_id, "paid_at": {"$gte": start, "$lte": end}},
            {"_id": 1},
        )
    ]
    folio_ids = [
        doc["_id"]
        for doc in db.guest_folios.find(
            {"prop_id": prop_id, "created_at": {"$gte": start, "$lte": end}},
            {"_id": 1},
        )
    ]
    booking_ids = [
        doc["_id"]
        for doc in db.booking_orders.find(
            {"prop_id": prop_id, "created_at": {"$gte": start, "$lte": end}},
            {"_id": 1},
        )
    ]

    return {
        "payment_ids": payment_ids,
        "folio_ids": folio_ids,
        "booking_ids": booking_ids,
    }


def open_shift(
    prop_id: int,
    shift_type: str,
    employee: str,
    cash_initial: float | None = None,
) -> dict[str, Any]:
    """Open a new reception shift.

    Closes any currently active shift for the same property first (auto-close).
    If ``cash_initial`` is not provided, it defaults to the ``cash_left``
    of the previous closed shift (carry-over).
    """
    if shift_type not in SHIFT_TYPES:
        raise ValueError(f"Invalid shift_type. Must be one of: {', '.join(SHIFT_TYPES)}")

    db = get_database()

    # Auto-close any active shift for this property
    active = db[RECEPTION_SHIFTS_COLLECTION].find_one(
        {"prop_id": prop_id, "status": "open"},
    )
    if active:
        try:
            close_shift(str(active["_id"]), cash_counted=0, closed_by="system (auto-close on new shift)")
        except Exception:
            logger.exception("Failed to auto-close previous shift for prop_id %s", prop_id)

    now = _now_iso()
    now_dt = _now_dt()
    hotel_id = resolve_hotel_id(prop_id)
    employee_id = resolve_employee_id(employee)

    # Carry-over: default initial cash from previous shift's cash_left
    if cash_initial is None:
        last_shift = _get_last_closed_shift(prop_id)
        if last_shift and last_shift.get("cash_left") is not None:
            cash_initial = float(last_shift["cash_left"])
        else:
            cash_initial = 0.0

    doc = {
        "prop_id": prop_id,
        "hotel_id": hotel_id,
        "shift_type": shift_type,
        "employee": employee,
        "employee_id": employee_id,
        "start_time": now,
        "end_time": None,
        "cash_initial": round(float(cash_initial), 2),
        "cash_counted": None,
        "cash_final": None,
        "cash_left": None,
        "cash_over_short": None,
        "closing_notes": None,
        "total_collected": 0.0,
        "status": "open",
        "closed_by": None,
        "closed_at": None,
        "transactions": [],
        "created_at": now,
        "payment_ids": [],
        "folio_ids": [],
        "booking_ids": [],
    }
    result = db[RECEPTION_SHIFTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    logger.info(
        "Shift opened — prop_id=%s type=%s employee=%s cash_initial=%.2f",
        prop_id, shift_type, employee, cash_initial,
    )
    return _enrich_shift(doc)


def _calc_payment_breakdown(transactions: list[dict]) -> dict[str, Any]:
    """Calculate totals by payment method from shift transactions."""
    breakdown: dict[str, float] = {}
    for txn in transactions:
        if txn.get("type") in ("check_out", "payment"):
            method = txn.get("payment_method", "other").lower().strip()
            if method not in ("cash", "card", "transfer", "other"):
                method = "other"
            amount = float(txn.get("amount", 0) or 0)
            breakdown[method] = round(breakdown.get(method, 0) + amount, 2)
    return {
        "cash": breakdown.get("cash", 0),
        "card": breakdown.get("card", 0),
        "transfer": breakdown.get("transfer", 0),
        "other": breakdown.get("other", 0),
        "total": round(sum(breakdown.values()), 2),
    }


def close_shift(
    shift_id: str,
    *,
    cash_counted: float = 0,
    cash_left: float | None = None,
    deposits: list[dict] | None = None,
    closing_notes: str = "",
    closed_by: str = "web",
) -> dict[str, Any] | None:
    """Close an open shift, calculating cash expected, over/short, cash left,
    and linking related payments, folios and bookings via ObjectId references.

    Args:
        cash_counted: Physical cash counted in the drawer.
        cash_left: Cash left in the drawer for the next shift. If not
            provided, it is calculated as ``cash_counted - deposit_total``.
        deposits: Optional list of deposit/drop records made during the shift.
            Each item: {"amount": float, "method": str, "notes": str}
        closing_notes: Free-text observations at close time.
        closed_by: Username or system identifier closing the shift.
    """
    db = get_database()
    now_dt = _now_dt()
    now_iso = now_dt.isoformat()

    shift = db[RECEPTION_SHIFTS_COLLECTION].find_one({"_id": ObjectId(shift_id)})
    if not shift:
        raise ValueError("Shift not found")
    if shift.get("status") != "open":
        raise ValueError("Shift is already closed")

    transactions = shift.get("transactions", [])
    total_collected = sum(
        float(txn.get("amount", 0) or 0)
        for txn in transactions
        if txn.get("type") in ("check_out", "payment")
    )

    # Calculate payment method breakdown
    payment_breakdown = _calc_payment_breakdown(transactions)

    # Calculate deposit totals. Only cash withdrawals/drops reduce the
    # physical cash left in the drawer.
    cash_deposit_total = 0.0
    deposit_total = 0.0
    if deposits:
        deposit_total = round(sum(float(d.get("amount", 0)) for d in deposits), 2)
        cash_deposit_total = round(
            sum(
                float(d.get("amount", 0))
                for d in deposits
                if str(d.get("method", "")).lower() in ("cash", "efectivo", "")
            ),
            2,
        )

    cash_initial = float(shift.get("cash_initial", 0) or 0)
    cash_expected = round(cash_initial + payment_breakdown["cash"], 2)
    cash_counted = round(float(cash_counted), 2)

    # cash_left defaults to counted minus cash deposits/drops
    if cash_left is None:
        cash_left = round(cash_counted - cash_deposit_total, 2)
    else:
        cash_left = round(float(cash_left), 2)

    cash_over_short = round(cash_counted - cash_expected, 2)

    # Collect related ObjectId references within the shift window
    start_dt = shift.get("start_time")
    if isinstance(start_dt, str):
        start_dt = datetime.fromisoformat(start_dt)
    related = _collect_related_ids(shift.get("prop_id", 0), start_dt, now_dt)

    update = {
        "$set": {
            "status": "closed",
            "cash_counted": cash_counted,
            "cash_left": cash_left,
            "cash_over_short": cash_over_short,
            "closing_notes": (closing_notes or "").strip(),
            "cash_final": cash_counted,
            "total_collected": round(total_collected, 2),
            "payment_breakdown": payment_breakdown,
            "deposit_total": deposit_total,
            "deposits": deposits or [],
            "closed_by": closed_by,
            "closed_at": now_iso,
            "end_time": now_iso,
            "payment_ids": related["payment_ids"],
            "folio_ids": related["folio_ids"],
            "booking_ids": related["booking_ids"],
        }
    }
    db[RECEPTION_SHIFTS_COLLECTION].update_one({"_id": ObjectId(shift_id)}, update)

    logger.info(
        "Shift closed — id=%s cash_counted=%.2f cash_expected=%.2f over_short=%.2f cash_left=%.2f payments=%d folios=%d bookings=%d",
        shift_id, cash_counted, cash_expected, cash_over_short, cash_left,
        len(related["payment_ids"]), len(related["folio_ids"]), len(related["booking_ids"]),
    )

    result = db[RECEPTION_SHIFTS_COLLECTION].find_one({"_id": ObjectId(shift_id)})
    enriched = _enrich_shift(result)
    enriched["cash_difference"] = cash_over_short
    enriched["cash_expected"] = cash_expected
    enriched["payment_breakdown"] = payment_breakdown
    enriched["deposit_total"] = deposit_total
    return enriched


def get_active_shift(prop_id: int) -> dict[str, Any] | None:
    """Get the currently active (open) shift for a property."""
    db = get_database()
    doc = db[RECEPTION_SHIFTS_COLLECTION].find_one(
        {"prop_id": prop_id, "status": "open"},
    )
    if not doc:
        return None
    return _enrich_shift(doc)


def get_shift(shift_id: str) -> dict[str, Any] | None:
    """Get a shift by its ID."""
    db = get_database()
    try:
        doc = db[RECEPTION_SHIFTS_COLLECTION].find_one({"_id": ObjectId(shift_id)})
    except Exception:
        return None
    if not doc:
        return None
    return _enrich_shift(doc)


def list_shifts(
    prop_id: int | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List shifts, newest first."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter

    docs = list(
        db[RECEPTION_SHIFTS_COLLECTION]
        .find(query)
        .sort("start_time", -1)
        .limit(limit)
    )
    return [_enrich_shift(d) for d in docs]


def list_shifts_for_cash_control(
    prop_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List closed shifts for manager cash-control view.

    Filters by optional date range (ISO date strings) and property.
    Returns newest first.
    """
    db = get_database()
    query: dict[str, Any] = {"status": "closed"}
    if prop_id:
        query["prop_id"] = prop_id

    date_filter: dict[str, Any] = {}
    if start_date:
        date_filter["$gte"] = start_date
    if end_date:
        date_filter["$lte"] = end_date
    if date_filter:
        query["closed_at"] = date_filter

    docs = list(
        db[RECEPTION_SHIFTS_COLLECTION]
        .find(query)
        .sort("closed_at", -1)
        .limit(limit)
    )
    return [_enrich_shift(d) for d in docs]


def register_transaction(
    prop_id: int,
    txn_type: str,
    booking_id: str,
    *,
    amount: float = 0,
    payment_method: str = "",
    description: str = "",
) -> dict[str, Any] | None:
    """Register a transaction on the active shift for a property.

    Types: check_in, check_out, payment, cancellation

    This is a fire-and-forget operation — failures are logged but never
    bubble up to interrupt the calling flow.
    """
    try:
        db = get_database()
        txn = {
            "transaction_id": _generate_txn_id(),
            "type": txn_type,
            "booking_id": booking_id,
            "amount": round(float(amount), 2),
            "payment_method": payment_method or "",
            "timestamp": _now_iso(),
            "description": description or f"{txn_type}: {booking_id}",
        }

        result = db[RECEPTION_SHIFTS_COLLECTION].update_one(
            {"prop_id": prop_id, "status": "open"},
            {
                "$push": {"transactions": txn},
                "$inc": {"total_collected": round(float(amount), 2)} if txn_type in ("check_out", "payment") else {},
            },
        )
        if result.modified_count == 0:
            logger.debug("No active shift found for prop_id=%s — txn not registered", prop_id)
            return None

        logger.debug(
            "Transaction registered — prop_id=%s type=%s booking=%s amount=%.2f",
            prop_id, txn_type, booking_id, amount,
        )
        return txn
    except Exception:
        logger.exception(
            "Failed to register transaction — prop_id=%s type=%s booking=%s",
            prop_id, txn_type, booking_id,
        )
        return None
