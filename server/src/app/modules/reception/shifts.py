from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from src.app.core.resolvers import resolve_hotel_id, resolve_employee_id, resolve_user_id

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

# Identifiers used by the service layer when no real user is responsible
# for an action. These intentionally map to a NULL FK instead of being
# resolved to a user account — otherwise an attacker could create a user
# literally named "system" and trick attribution.
SYSTEM_ACTOR_IDS: frozenset[str] = frozenset({"system", "cron", "etl"})


def _resolve_actor_id(actor: str) -> "ObjectId | None":
    """Resolve a `users` actor name to ``users._id``, except for system actors.

    System identifiers ("system", "cron", "etl") are intentionally NOT
    looked up in the ``users`` collection — we don't want force-close /
    cron / etl actions to be attributed to any FK (or worse, to a real
    user account that happens to share those names). They get ``None``
    and the FK field is empty.
    """
    if not actor:
        return None
    if actor in SYSTEM_ACTOR_IDS:
        return None
    return resolve_user_id(actor)


class ActiveShiftExistsError(Exception):
    """Raised when ``open_shift`` is called while another shift is active.

    Carries enough structured data for the caller (routes layer) to
    surface a 409 with the active shift snapshot + the most recent
    closed shift's ``cash_over_short`` so the UI can disable the
    force-close button when there's an unresolved over/short.
    """

    def __init__(
        self,
        *,
        active_shift: dict[str, Any],
        transactions_count: int,
        total_collected: float,
        last_closed_over_short: float | None,
    ) -> None:
        super().__init__("An active shift already exists for this property")
        self.active_shift = active_shift
        self.transactions_count = transactions_count
        self.total_collected = total_collected
        self.last_closed_over_short = last_closed_over_short


class ScheduleMismatchError(Exception):
    """Raised when ``open_shift`` is called with a ``shift_type`` that does
    not match the EXPECTED shift_type for the current moment.

    The expectation is resolved by ``resolve_expected_shift_type`` which
    prefers HR's ``employee_shifts.scheduled_start``/``scheduled_end``
    windows for the authenticated opener, and falls back to a clock-hour
    heuristic when no HR record exists for today.

    The 422 response carries enough structure for the frontend to surface
    an override modal that only gerente_hotel / super_admin (``shifts.manage``
    permission) may resolve.
    """

    def __init__(
        self,
        *,
        requested: str,
        expected: str,
        source: str,
        opener_username: str,
        now_local: datetime,
        expected_window: str,
    ) -> None:
        super().__init__(
            f"Requested shift_type={requested!r} does not match expected={expected!r}"
        )
        self.requested = requested
        self.expected = expected
        self.source = source  # "schedule" | "time_of_day"
        self.opener_username = opener_username
        self.now_local = now_local
        self.expected_window = expected_window


def _shift_type_for_hour(hour: int) -> str:
    """Pure time-of-day heuristic matching ``DEFAULT_SHIFT_HOURS``.

    - 00:00–07:59  → evening
    - 08:00–15:59  → morning
    - 16:00–23:59  → afternoon
    """
    if 0 <= hour < 8:
        return "evening"
    if 8 <= hour < 16:
        return "morning"
    return "afternoon"


def _parse_hhmm(text: str) -> tuple[int, int] | None:
    """Parse an ``HH:MM`` string into (hour, minute). Returns None on bad input."""
    if not text or ":" not in text:
        return None
    try:
        parts = text.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (ValueError, IndexError):
        return None
    return None


def _shift_type_for_window(start_hhmm: str, end_hhmm: str) -> tuple[str, str] | None:
    """Map an HR-schedule window ``start-end`` (HH:MM-HH:MM) into the closest
    of our 3 cashier ``shift_type`` buckets.

    Handles wrap-past-midnight windows (e.g. afternoon 16:00 -> 00:00) by
    inspecting the midpoint of the window. Returns ``None`` for empty/
    malformed windows so the caller can fall back to the clock heuristic.
    """
    start = _parse_hhmm(start_hhmm)
    end = _parse_hhmm(end_hhmm)
    if start is None or end is None:
        return None
    s_h, s_m = start
    e_h, e_m = end

    # Compute duration; if end <= start the window wraps midnight
    s_minutes = s_h * 60 + s_m
    e_minutes = e_h * 60 + e_m
    if e_minutes <= s_minutes:
        # Wrap: add 24h to end so the span is positive.
        e_minutes += 24 * 60
    duration_min = e_minutes - s_minutes
    if duration_min <= 0 or duration_min > 24 * 60:
        return None

    # Use the midpoint of the window (also unwrapped) to assign the bucket.
    mid_minutes = s_minutes + duration_min // 2
    mid_hour = (mid_minutes // 60) % 24
    bucket = _shift_type_for_hour(mid_hour)
    return bucket, f"{start_hhmm}-{end_hhmm}"


def resolve_expected_shift_type(opened_by: str, at_dt: datetime) -> tuple[str, str]:
    """Resolve the EXPECTED ``shift_type`` for ``opened_by`` at ``at_dt``.

    Returns ``(expected_shift_type, source)`` where ``source`` is one of:
      - ``"schedule"``: an HR ``employee_shifts`` row exists for this user today.
      - ``"time_of_day"``: no HR record; using clock-hour heuristic.

    A MOCK for payroll/hr hours — once HR wires the schedule properly, the
    fallback will rarely fire in production.
    """
    db = get_database()

    # ── Source 1: HR schedule (per-opener, today) ────────────────────
    try:
        user = db.users.find_one({"username": opened_by}, {"_id": 1})
        if user:
            user_id = str(user["_id"])
            emp = db.employees.find_one({"user_id": user_id}, {"_id": 1})
            if emp:
                emp_id = str(emp["_id"])
                today_str = at_dt.date().strftime("%Y-%m-%d")
                today_shift = db.employee_shifts.find_one(
                    {
                        "employee_id": emp_id,
                        "date": today_str,
                        "status": {"$in": ["pending", "active"]},
                    },
                    {"scheduled_start": 1, "scheduled_end": 1, "shift_type": 1},
                )
                if today_shift:
                    # Prefer an explicit shift_type field if HR has populated it.
                    explicit = today_shift.get("shift_type")
                    if explicit in SHIFT_TYPES:
                        return explicit, "schedule"
                    # Otherwise map the scheduled_start/scheduled_end window.
                    mapped = _shift_type_for_window(
                        today_shift.get("scheduled_start", ""),
                        today_shift.get("scheduled_end", ""),
                    )
                    if mapped is not None:
                        return mapped[0], "schedule"
    except Exception:
        # Any failure in HR lookup must NOT block schedule validation —
        # we ALWAYS have the clock-hour fallback beneath.
        logger.debug("HR schedule lookup failed for %s; using time-of-day", opened_by)

    # ── Source 2: time-of-day heuristic (mock fallback) ───────────────
    return _shift_type_for_hour(at_dt.hour), "time_of_day"


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
    # Stringify FK ObjectIds for JSON responses
    for f in ("opened_by_id", "closed_by_id"):
        if f in doc and doc[f] is not None:
            doc[f] = str(doc[f])
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
    *,
    force: bool = False,
    bypass_schedule_check: bool = False,
    opened_by: str,
) -> dict[str, Any]:
    """Open a new reception shift.

    If a shift is already active for the same property:
      - with ``force=False`` (default), raise ``ValueError`` so the caller
        can return HTTP 409 with the active shift's full payload for the
        frontend to render a confirmation modal.
      - with ``force=True``, auto-close the previous shift WITHOUT
        reconciliation (logs a WARNING line for audit) and proceed.

    Schedule validation (CU-Recep-02):
      - The shift_type must match the EXPECTED cash-window for NOW.
        Expected bucket is resolved from the HR ``employee_shifts`` row for
        this opener today, falling back to a clock-hour heuristic.
      - With ``bypass_schedule_check=True`` (recepcionista passing in
        gerente_hotel / super_admin credentials), the check is skipped and
        a WARNING is logged for audit. The route layer must independently
        verify the caller has ``shifts.manage`` before forwarding True.

    If ``cash_initial`` is not provided, it defaults to the ``cash_left``
    of the previous closed shift (carry-over).
    """
    if shift_type not in SHIFT_TYPES:
        raise ValueError(f"Invalid shift_type. Must be one of: {', '.join(SHIFT_TYPES)}")

    db = get_database()

    # Resolve pre-existing active shift (if any) BEFORE doing anything else,
    # so the 409 response can carry the snapshot for the confirmation modal.
    active = db[RECEPTION_SHIFTS_COLLECTION].find_one(
        {"prop_id": prop_id, "status": "open"},
    )
    if active and not force:
        # Re-fetch last closed shift so the 409 detail can also flag whether
        # the prior close had any over/short. The frontend uses this to
        # disable the force-close button when the previous close was
        # unbalanced.
        last_closed = _get_last_closed_shift(prop_id)
        last_closed_over_short = (
            float(last_closed.get("cash_over_short"))
            if last_closed and last_closed.get("cash_over_short") is not None
            else None
        )
        transactions_count = len(active.get("transactions", []))
        total_collected = round(
            sum(
                float(t.get("amount", 0) or 0)
                for t in active.get("transactions", [])
                if t.get("type") in ("check_out", "payment")
            ),
            2,
        )
        raise ActiveShiftExistsError(
            active_shift=_enrich_shift(dict(active)),
            transactions_count=transactions_count,
            total_collected=total_collected,
            last_closed_over_short=last_closed_over_short,
        )

    if active and force:
        # ── SERVER-SIDE FORCE GUARD (defense in depth) ──
        # The UI disables "Forzar Cierre y Abrir Nuevo" when the most-recent
        # CLOSED shift has a non-zero cash_over_short. We MUST replicate
        # that gate at the API layer — a direct curl with force=true would
        # otherwise silently auto-close a shift with an unresolved discrepancy.
        last_closed = _get_last_closed_shift(prop_id)
        last_closed_over_short = (
            float(last_closed.get("cash_over_short"))
            if last_closed and last_closed.get("cash_over_short") is not None
            else None
        )
        if last_closed_over_short is not None and abs(last_closed_over_short) > 0:
            transactions_count = len(active.get("transactions", []))
            total_collected = round(
                sum(
                    float(t.get("amount", 0) or 0)
                    for t in active.get("transactions", [])
                    if t.get("type") in ("check_out", "payment")
                ),
                2,
            )
            logger.warning(
                "FORCE-CLOSE BLOCKED for prop_id=%s — most-recent CLOSED shift "
                "has cash_over_short=%.2f (initiated by user=%s)",
                prop_id, last_closed_over_short, opened_by,
            )
            raise ActiveShiftExistsError(
                active_shift=_enrich_shift(dict(active)),
                transactions_count=transactions_count,
                total_collected=total_collected,
                last_closed_over_short=last_closed_over_short,
            )

        logger.warning(
            "FORCE-CLOSING active shift id=%s without reconciliation (requested by user=%s, "
            "employee label=%s, prop_id=%s)",
            active["_id"], opened_by, employee, prop_id,
        )
        try:
            # The opener is causally responsible for the prior shift being
            # auto-closed without reconciliation. We mark closed_by as the
            # system identifier and embed the real actor in closing_notes
            # so audit logs can reconstruct what happened.
            close_shift(
                str(active["_id"]),
                cash_counted=0,
                closing_notes=(
                    f"force-closed via open_shift(force=true) — decision-maker="
                    f"'{opened_by}' (employee visual label='{employee}')"
                ),
                closed_by="system",
            )
        except Exception:
            logger.exception("Failed to force-close previous shift for prop_id %s", prop_id)

    # ── Schedule validation runs AFTER the active-shift conflict check so
    #    that a 409 (reconcile-cash-first) always wins over a 422
    #    (schedule-mismatch) when both apply. Losing the active shift's
    #    transactions is the more critical invariant — don't mask that
    #    warning behind a schedule-hour error. ──
    now_dt = _now_dt()
    if not bypass_schedule_check:
        expected, source = resolve_expected_shift_type(opened_by, now_dt)
        if expected != shift_type:
            logger.info(
                "Schedule validation REJECTED — prop_id=%s opener=%s requested=%s "
                "expected=%s source=%s",
                prop_id, opened_by, shift_type, expected, source,
            )
            default_window = (
                f"{DEFAULT_SHIFT_HOURS[expected]['start']}-{DEFAULT_SHIFT_HOURS[expected]['end']}"
            )
            raise ScheduleMismatchError(
                requested=shift_type,
                expected=expected,
                source=source,
                opener_username=opened_by,
                now_local=now_dt,
                expected_window=default_window,
            )
    else:
        logger.warning(
            "SCHEDULE BYPASSED — prop_id=%s opener=%s requested_type=%s (audit: gerente override)",
            prop_id, opened_by, shift_type,
        )

    now = _now_iso()
    # ``now_dt`` is already computed by the schedule-validation block above
    # when it runs; we reuse it here. Avoid a redundant call so audit logs
    # don't have microsecond drift between two timestamps.
    hotel_id = resolve_hotel_id(prop_id)
    employee_id = resolve_employee_id(employee)
    opened_by_id = _resolve_actor_id(opened_by)

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
        "opened_by": opened_by,
        "opened_by_id": opened_by_id,
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
        "closed_by_id": None,
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
        "Shift opened — prop_id=%s type=%s employee_label=%s opened_by=%s opened_by_id=%s cash_initial=%.2f",
        prop_id, shift_type, employee, opened_by, opened_by_id, cash_initial,
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
    closed_by: str,
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
            "closed_by_id": _resolve_actor_id(closed_by),
            "closed_at": now_iso,
            "end_time": now_iso,
            "payment_ids": related["payment_ids"],
            "folio_ids": related["folio_ids"],
            "booking_ids": related["booking_ids"],
        }
    }
    db[RECEPTION_SHIFTS_COLLECTION].update_one({"_id": ObjectId(shift_id)}, update)

    logger.info(
        "Shift closed — id=%s closed_by=%s cash_counted=%.2f cash_expected=%.2f over_short=%.2f cash_left=%.2f payments=%d folios=%d bookings=%d",
        shift_id, closed_by, cash_counted, cash_expected, cash_over_short, cash_left,
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
