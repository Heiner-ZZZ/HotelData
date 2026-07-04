from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

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


def open_shift(
    prop_id: int,
    shift_type: str,
    employee: str,
    cash_initial: float = 0,
) -> dict[str, Any]:
    """Open a new reception shift.

    Closes any currently active shift for the same property first (auto-close).
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
            close_shift(str(active["_id"]), cash_final=0, closed_by="system (auto-close on new shift)")
        except Exception:
            logger.exception("Failed to auto-close previous shift for prop_id %s", prop_id)

    now = _now_iso()
    doc = {
        "prop_id": prop_id,
        "shift_type": shift_type,
        "employee": employee,
        "start_time": now,
        "end_time": None,
        "cash_initial": round(float(cash_initial), 2),
        "cash_final": None,
        "total_collected": 0.0,
        "status": "open",
        "closed_by": None,
        "closed_at": None,
        "transactions": [],
        "created_at": now,
    }
    result = db[RECEPTION_SHIFTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    logger.info("Shift opened — prop_id=%s type=%s employee=%s cash=%.2f", prop_id, shift_type, employee, cash_initial)
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
    cash_final: float = 0,
    closed_by: str = "web",
    deposits: list[dict] | None = None,
) -> dict[str, Any] | None:
    """Close an open shift, calculating total_collected, cash difference,
    and payment method breakdown.

    Args:
        deposits: Optional list of deposit records made during the shift.
                  Each item: {"amount": float, "method": str, "notes": str}
    """
    db = get_database()
    now = _now_iso()

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

    # Calculate deposit totals
    deposit_total = 0.0
    if deposits:
        deposit_total = round(sum(float(d.get("amount", 0)) for d in deposits), 2)

    cash_diff = round(float(cash_final) - float(shift.get("cash_initial", 0)), 2)
    cash_expected = round(payment_breakdown["cash"], 2)

    update = {
        "$set": {
            "status": "closed",
            "cash_final": round(float(cash_final), 2),
            "total_collected": round(total_collected, 2),
            "payment_breakdown": payment_breakdown,
            "deposit_total": deposit_total,
            "deposits": deposits or [],
            "closed_by": closed_by,
            "closed_at": now,
            "end_time": now,
        }
    }
    db[RECEPTION_SHIFTS_COLLECTION].update_one({"_id": ObjectId(shift_id)}, update)

    logger.info(
        "Shift closed — id=%s cash_final=%.2f collected=%.2f diff=%.2f cash_expected=%.2f",
        shift_id, cash_final, total_collected, cash_diff, cash_expected,
    )

    result = db[RECEPTION_SHIFTS_COLLECTION].find_one({"_id": ObjectId(shift_id)})
    enriched = _enrich_shift(result)
    enriched["cash_difference"] = cash_diff
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
