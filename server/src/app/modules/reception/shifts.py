from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId

from src.app.core.resolvers import resolve_hotel_id, resolve_employee_id, resolve_user_id

from .collections import (
    RECEPTION_SHIFT_CONFIG_COLLECTION,
    RECEPTION_SHIFTS_COLLECTION,
)
from src.database.connection import get_database

logger = logging.getLogger(__name__)

SHIFT_TYPES = ("morning", "afternoon", "evening")

# Display names per shift type; labels pair the name with the effective
# window (e.g. "Matutino (08:00-16:00)") so a per-hotel config change is
# reflected everywhere the type is shown.
SHIFT_TYPE_NAMES = {
    "morning": "Matutino",
    "afternoon": "Vespertino",
    "evening": "Nocturno",
}

DEFAULT_SHIFT_HOURS = {
    "morning": {"start": "08:00", "end": "16:00"},
    "afternoon": {"start": "16:00", "end": "00:00"},
    "evening": {"start": "00:00", "end": "08:00"},
}

# A shift may stay open at most this many hours before front-desk cash
# operations (cash payments, walk-ins, check-in/out) are blocked. Per-hotel
# override lives in ``reception_shift_config.max_open_hours``.
DEFAULT_MAX_OPEN_HOURS = 12.0

# Hard cap on the configurable limit (30 days) — prevents a misconfiguration
# from effectively disabling the control.
MAX_OPEN_HOURS_CAP_HOURS = 24 * 30

# A shift that has been open at least this many hours triggers an internal
# ``shift_open_long`` notification to the hotel manager as a heads-up
# (before the max-open block kicks in). Per-hotel override lives in
# ``reception_shift_config.notify_manager_hours``.
DEFAULT_NOTIFY_MANAGER_HOURS = 8.0


def _window_to_label(shift_type: str, start: str, end: str) -> str:
    return f"{SHIFT_TYPE_NAMES.get(shift_type, shift_type)} ({start}-{end})"


# Default labels — kept as a constant for backward-compatible imports; the
# live labels for a property are resolved from ``get_shift_labels(prop_id)``.
SHIFT_TYPE_LABELS = {
    t: _window_to_label(t, DEFAULT_SHIFT_HOURS[t]["start"], DEFAULT_SHIFT_HOURS[t]["end"])
    for t in SHIFT_TYPES
}

# Identifiers used by the service layer when no real user is responsible
# for an action. These intentionally map to a NULL FK instead of being
# resolved to a user account — otherwise an attacker could create a user
# literally named "system" and trick attribution.
SYSTEM_ACTOR_IDS: frozenset[str] = frozenset({"system", "cron", "etl"})

# Booking channels that are NEVER tied to a cash shift. Web reservations are
# not front-desk cashier operations — the close-of-shift snapshot and the
# per-document ``shift_id`` FK must agree on this rule.
WEB_CHANNEL_SOURCES: frozenset[str] = frozenset({
    "web_request",
    "web",
    "booking_engine",
    "direct",
    "direct_website",
    "ota",
    "booking.com",
    "expedia",
    "cliente",
})


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


class ShiftExpiredError(Exception):
    """The active shift for a property has exceeded its max-open hours.

    Front-desk cash operations stay blocked until the shift is closed; the
    shift itself remains ``status=open`` (the drawer still holds cash) but
    no new cash movements may be recorded against it.
    """

    def __init__(
        self,
        *,
        shift_id: str,
        prop_id: int,
        opened_at: str | None = None,
        max_open_hours: float = DEFAULT_MAX_OPEN_HOURS,
        opened_by: str | None = None,
    ) -> None:
        super().__init__(
            f"Active shift {shift_id} for prop_id={prop_id} exceeded max open hours"
        )
        self.shift_id = shift_id
        self.prop_id = prop_id
        self.opened_at = opened_at
        self.max_open_hours = max_open_hours
        self.opened_by = opened_by

    @property
    def message(self) -> str:
        opened = (
            f" (abierto el {self.opened_at})" if self.opened_at else ""
        )
        return (
            f"El turno activo lleva más de {self.max_open_hours:g} horas sin cerrarse"
            f"{opened}. Cierra el turno en Cajas y Turnos para desbloquear las "
            "operaciones de caja."
        )


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


def _hour_in_window(hour: int, window: dict) -> bool:
    """Whether ``hour`` (0-23) falls inside a ``{start, end}`` HH:MM window.

    Windows that wrap past midnight (e.g. 22:00-06:00) are handled by
    testing the minute-of-day and the minute-of-day+24h against the
    unwrapped span.
    """
    start = _parse_hhmm(str(window.get("start", "")))
    end = _parse_hhmm(str(window.get("end", "")))
    if start is None or end is None:
        return False
    s_min = start[0] * 60 + start[1]
    e_min = end[0] * 60 + end[1]
    if e_min <= s_min:
        e_min += 24 * 60
    m = (hour % 24) * 60
    return s_min <= m < e_min or s_min <= m + 24 * 60 < e_min


def _shift_type_for_hour(hour: int, windows: dict | None = None) -> str:
    """Time-of-day heuristic over the (optionally configured) windows.

    With the canonical defaults:
    - 00:00–07:59  → evening
    - 08:00–15:59  → morning
    - 16:00–23:59  → afternoon

    When ``windows`` (per-property config) is provided, the hour is
    classified against those windows instead. Hours not covered by any
    configured window — or an ambiguous overlap — fall back to the
    canonical defaults so the heuristic never returns None.
    """
    cfg = windows or DEFAULT_SHIFT_HOURS
    hits = [t for t in SHIFT_TYPES if _hour_in_window(hour, cfg[t])]
    if len(hits) == 1:
        return hits[0]
    default_hits = [t for t in SHIFT_TYPES if _hour_in_window(hour, DEFAULT_SHIFT_HOURS[t])]
    return default_hits[0] if len(default_hits) == 1 else "morning"


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


def _shift_type_for_window(start_hhmm: str, end_hhmm: str, windows: dict | None = None) -> tuple[str, str] | None:
    """Map an HR-schedule window ``start-end`` (HH:MM-HH:MM) into the closest
    of our 3 cashier ``shift_type`` buckets.

    Handles wrap-past-midnight windows (e.g. afternoon 16:00 -> 00:00) by
    inspecting the midpoint of the window, classified against the
    property's configured windows when provided. Returns ``None`` for
    empty/malformed windows so the caller can fall back to the clock
    heuristic.
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
    bucket = _shift_type_for_hour(mid_hour, windows)
    return bucket, f"{start_hhmm}-{end_hhmm}"


def resolve_expected_shift_type(
    opened_by: str,
    at_dt: datetime,
    prop_id: int | None = None,
) -> tuple[str, str]:
    """Resolve the EXPECTED ``shift_type`` for ``opened_by`` at ``at_dt``.

    Returns ``(expected_shift_type, source)`` where ``source`` is one of:
      - ``"schedule"``: an HR ``employee_shifts`` row exists for this user today.
      - ``"time_of_day"``: no HR record; using clock-hour heuristic.

    When ``prop_id`` is given, the configured per-property windows drive
    the classification; otherwise the canonical ``DEFAULT_SHIFT_HOURS``
    are used.

    A MOCK for payroll/hr hours — once HR wires the schedule properly, the
    fallback will rarely fire in production.
    """
    db = get_database()
    windows = get_shift_windows(prop_id) if prop_id else None

    # ── Source 1: HR schedule (per-opener, today) ────────────────────
    try:
        user = db.users.find_one({"username": opened_by}, {"_id": 1})
        if user:
            user_id = user["_id"]
            emp = db.employees.find_one({"user_id": user_id}, {"_id": 1})
            if emp:
                emp_id = emp["_id"]
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
                        windows,
                    )
                    if mapped is not None:
                        return mapped[0], "schedule"
    except Exception:
        # Any failure in HR lookup must NOT block schedule validation —
        # we ALWAYS have the clock-hour fallback beneath.
        logger.debug("HR schedule lookup failed for %s; using time-of-day", opened_by)

    # ── Source 2: time-of-day heuristic (mock fallback) ───────────────
    return _shift_type_for_hour(at_dt.hour, windows), "time_of_day"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


# ── Per-hotel shift-window configuration ─────────────────────────────────


def get_shift_windows(prop_id: int) -> dict[str, dict[str, str]]:
    """Effective HH:MM windows for a property (custom config over defaults)."""
    db = get_database()
    doc = db[RECEPTION_SHIFT_CONFIG_COLLECTION].find_one({"prop_id": prop_id})
    windows = {
        t: {"start": DEFAULT_SHIFT_HOURS[t]["start"], "end": DEFAULT_SHIFT_HOURS[t]["end"]}
        for t in SHIFT_TYPES
    }
    if doc and isinstance(doc.get("windows"), dict):
        for t in SHIFT_TYPES:
            w = doc["windows"].get(t)
            if isinstance(w, dict) and w.get("start") and w.get("end"):
                windows[t] = {"start": str(w["start"]), "end": str(w["end"])}
    return windows


def get_shift_labels(prop_id: int) -> dict[str, str]:
    """Human labels for each shift type at a property ("Matutino (10:00-18:00)")."""
    windows = get_shift_windows(prop_id)
    return {
        t: _window_to_label(t, windows[t]["start"], windows[t]["end"])
        for t in SHIFT_TYPES
    }


def _max_open_hours_for_doc(doc: dict | None) -> float:
    """Effective max-open-hours from a config doc (custom over default)."""
    if doc and isinstance(doc.get("max_open_hours"), (int, float)):
        try:
            value = float(doc["max_open_hours"])
        except (TypeError, ValueError):
            return DEFAULT_MAX_OPEN_HOURS
        if 0 < value <= MAX_OPEN_HOURS_CAP_HOURS:
            return value
    return DEFAULT_MAX_OPEN_HOURS


def _shift_expired(start_time: Any, max_open_hours: float, now: datetime) -> bool:
    """Whether a shift started at ``start_time`` is past its max-open window."""
    if not start_time:
        return False
    try:
        start = datetime.fromisoformat(str(start_time))
    except (TypeError, ValueError):
        return False
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return now >= start + timedelta(hours=max_open_hours)


def get_shift_config(prop_id: int) -> dict[str, Any]:
    """Full shift config for a property (windows + labels + audit + max hours).

    When no custom doc exists, returns the canonical defaults with
    ``is_custom=False`` so clients can render the same shape either way.
    """
    db = get_database()
    doc = db[RECEPTION_SHIFT_CONFIG_COLLECTION].find_one({"prop_id": prop_id})
    windows = get_shift_windows(prop_id)
    return {
        "prop_id": prop_id,
        "windows": windows,
        "labels": {
            t: _window_to_label(t, windows[t]["start"], windows[t]["end"])
            for t in SHIFT_TYPES
        },
        "max_open_hours": _max_open_hours_for_doc(doc),
        "notify_manager_hours": _notify_manager_hours_for_doc(doc),
        "is_custom": doc is not None,
        "updated_at": (
            doc["updated_at"].isoformat()
            if doc and isinstance(doc.get("updated_at"), datetime)
            else None
        ),
        "updated_by": doc.get("updated_by") if doc else None,
    }


def _window_minutes(window: dict) -> tuple[int, int] | None:
    """Raw ``(start_min, end_min)`` of a HH:MM window (no midnight unwrap)."""
    start = _parse_hhmm(str(window.get("start", "")))
    end = _parse_hhmm(str(window.get("end", "")))
    if start is None or end is None:
        return None
    return start[0] * 60 + start[1], end[0] * 60 + end[1]


def _window_intervals(window: dict) -> list[tuple[int, int]]:
    """Coverage of a window as minute-of-day intervals within [0, 1440).

    A window that wraps past midnight (end < start) covers two intervals:
    [start, 1440) and [0, end).
    """
    raw = _window_minutes(window)
    if raw is None:
        return []
    s, e = raw
    if e == s:
        return []
    if e > s:
        return [(s, e)]
    return [(s, 1440), (0, e)]


def _intervals_overlap(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> bool:
    for s1, e1 in a:
        for s2, e2 in b:
            if s1 < e2 and s2 < e1:
                return True
    return False


def _validate_windows(windows: dict) -> dict[str, dict[str, str]]:
    """Normalize + validate a full set of per-type windows.

    Raises ``ValueError`` (human-readable Spanish message) on any malformed
    window: bad HH:MM, zero/overlong duration, or overlapping coverage.
    """
    if not isinstance(windows, dict):
        raise ValueError("windows debe ser un objeto con las 3 ventanas")
    normalized: dict[str, dict[str, str]] = {}
    parsed: dict[str, list[tuple[int, int]]] = {}
    for t in SHIFT_TYPES:
        w = windows.get(t)
        if not isinstance(w, dict):
            raise ValueError(f"Falta la ventana para el turno {t}")
        start = str(w.get("start", "")).strip()
        end = str(w.get("end", "")).strip()
        raw = _window_minutes({"start": start, "end": end})
        if raw is None:
            raise ValueError(f"Horario inválido para el turno {t}: usa HH:MM (ej. 08:00)")
        s_min, e_min = raw
        # ``e == s`` is ambiguous (0 minutes vs 24h) — reject as zero-length.
        duration = e_min - s_min if e_min >= s_min else (24 * 60 - s_min) + e_min
        if duration <= 0:
            raise ValueError(f"Duración inválida para el turno {t}: debe ser mayor a 0 minutos")
        if duration > 24 * 60:
            raise ValueError(f"Duración inválida para el turno {t}: no puede superar 24 horas")
        normalized[t] = {"start": start, "end": end}
        parsed[t] = _window_intervals({"start": start, "end": end})
    for i, a in enumerate(SHIFT_TYPES):
        for b in SHIFT_TYPES[i + 1:]:
            if _intervals_overlap(parsed[a], parsed[b]):
                raise ValueError(
                    f"Las ventanas de {a} y {b} se superponen: "
                    "cada hora debe pertenecer a un solo turno"
                )
    return normalized


def _notify_manager_hours_for_doc(doc: dict | None) -> float:
    """Effective notify-manager hours from a config doc (custom over default)."""
    if doc and isinstance(doc.get("notify_manager_hours"), (int, float)):
        try:
            value = float(doc["notify_manager_hours"])
        except (TypeError, ValueError):
            return DEFAULT_NOTIFY_MANAGER_HOURS
        if 0 < value <= MAX_OPEN_HOURS_CAP_HOURS:
            return value
    return DEFAULT_NOTIFY_MANAGER_HOURS


def upsert_shift_config(
    prop_id: int,
    windows: dict,
    max_open_hours: float | None = None,
    notify_manager_hours: float | None = None,
    updated_by: str = "system",
) -> dict[str, Any]:
    """Persist custom cash-shift windows for a property (upsert).

    ``max_open_hours`` (optional) sets the per-hotel limit a shift may stay
    open before front-desk cash operations are blocked. When omitted, the
    existing value (or the default) is kept.

    ``notify_manager_hours`` (optional) sets the per-hotel threshold at
    which an internal ``shift_open_long`` notification is sent to the hotel
    manager. When omitted, the existing value (or the default) is kept.
    """
    normalized = _validate_windows(windows)
    now = _now_dt()
    set_doc: dict[str, Any] = {
        "windows": normalized,
        "updated_at": now,
        "updated_by": updated_by,
    }
    if max_open_hours is not None:
        try:
            value = float(max_open_hours)
        except (TypeError, ValueError) as exc:
            raise ValueError("Máximo de horas abierto inválido: debe ser un número") from exc
        if not (0 < value <= MAX_OPEN_HOURS_CAP_HOURS):
            raise ValueError(
                f"Máximo de horas abierto inválido: debe estar entre 0 y "
                f"{MAX_OPEN_HOURS_CAP_HOURS} horas"
            )
        set_doc["max_open_hours"] = round(value, 2)
    if notify_manager_hours is not None:
        try:
            value = float(notify_manager_hours)
        except (TypeError, ValueError) as exc:
            raise ValueError("Aviso al gerente inválido: debe ser un número") from exc
        if not (0 < value <= MAX_OPEN_HOURS_CAP_HOURS):
            raise ValueError(
                f"Aviso al gerente inválido: debe estar entre 0 y "
                f"{MAX_OPEN_HOURS_CAP_HOURS} horas"
            )
        set_doc["notify_manager_hours"] = round(value, 2)
    db = get_database()
    db[RECEPTION_SHIFT_CONFIG_COLLECTION].update_one(
        {"prop_id": prop_id},
        {"$set": set_doc},
        upsert=True,
    )
    return get_shift_config(prop_id)


def ensure_shift_not_expired(prop_id: int) -> None:
    """Raise ``ShiftExpiredError`` when the active shift is past its limit.

    No-op when there is no active shift (the callers already 409 on that
    case with their own message). Front-desk cash operations call this right
    after resolving the active shift id.
    """
    db = get_database()
    doc = db[RECEPTION_SHIFTS_COLLECTION].find_one(
        {"prop_id": prop_id, "status": "open"},
    )
    if not doc:
        return
    config_doc = db[RECEPTION_SHIFT_CONFIG_COLLECTION].find_one({"prop_id": prop_id})
    max_open_hours = _max_open_hours_for_doc(config_doc)
    if _shift_expired(doc.get("start_time"), max_open_hours, _now_dt()):
        raise ShiftExpiredError(
            shift_id=str(doc["_id"]),
            prop_id=prop_id,
            opened_at=doc.get("start_time"),
            max_open_hours=max_open_hours,
            opened_by=doc.get("opened_by"),
        )


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
            {
                "prop_id": prop_id,
                "created_at": {"$gte": start, "$lte": end},
                # Web-channel reservations are not cashier operations — they
                # must not appear in the shift's booking snapshot (same rule
                # as the live ``shift_id`` FK stamping).
                "booking_source": {"$nin": list(WEB_CHANNEL_SOURCES)},
            },
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
        expected, source = resolve_expected_shift_type(opened_by, now_dt, prop_id=prop_id)
        if expected != shift_type:
            logger.info(
                "Schedule validation REJECTED — prop_id=%s opener=%s requested=%s "
                "expected=%s source=%s",
                prop_id, opened_by, shift_type, expected, source,
            )
            windows = get_shift_windows(prop_id)
            expected_window = (
                f"{windows[expected]['start']}-{windows[expected]['end']}"
            )
            raise ScheduleMismatchError(
                requested=shift_type,
                expected=expected,
                source=source,
                opener_username=opened_by,
                now_local=now_dt,
                expected_window=expected_window,
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
    emergency: bool = False,
    emergency_reason: str = "",
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
        emergency: Mark this close as an *emergency close* (manager-only,
            for expired shifts that block cash operations). Stamps
            ``close_mode="emergency"`` and the reason on the shift doc so
            the simplified arqueo is traceable.
        emergency_reason: Why the shift needed an emergency close. Defaults
            to ``"vencimiento"`` when ``emergency=True``.
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

    # Emergency close markers (simplified arqueo for expired shifts). The
    # permission gate (``shifts.manage``) is enforced in the route layer.
    # Only stamped when emergency=True so normal closes stay unpolluted.
    close_mode = "emergency" if emergency else None
    close_reason = (emergency_reason or "vencimiento").strip() if emergency else ""

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
    if close_mode:
        update["$set"]["close_mode"] = close_mode
        update["$set"]["emergency_reason"] = close_reason or "vencimiento"
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


def _stamped_drawer_breakdown(doc: dict) -> tuple[float, int, dict[str, float]]:
    """Stamped payments missing from the drawer, with per-method totals.

    The shift's ``total_collected`` only reflects movements registered via
    ``register_transaction`` (check-out settlements, counter payments).
    Payments created through the billing module are stamped with
    ``shift_id`` but never push a shift transaction, so they would be
    invisible in the open-shifts view. We add them here, EXCLUDING any
    payment already represented as a ``check_out``/``payment`` transaction
    (matched by booking_id + amount) so the check-out settlement is not
    double-counted. Only ``confirmed`` payments count; failed/refunded/
    unapplied money never entered the drawer.

    Returns ``(additional_total, stamped_count, by_method)`` where
    ``by_method`` is ``{cash, card, transfer, other}`` of the additions —
    the per-method slice needed for the expected-arqueo summary.
    """
    db = get_database()
    shift_id = doc.get("_id")
    empty = {"cash": 0.0, "card": 0.0, "transfer": 0.0, "other": 0.0}
    if not shift_id:
        return 0.0, 0, empty

    counted: set[tuple[str, float]] = set()
    for txn in doc.get("transactions") or []:
        if txn.get("type") in ("check_out", "payment"):
            amount = round(float(txn.get("amount", 0) or 0), 2)
            if amount > 0:
                counted.add((str(txn.get("booking_id") or ""), amount))

    docs = list(
        db.reservation_payments.find(
            {"shift_id": shift_id, "status": "confirmed"},
            {"booking_id": 1, "amount": 1, "method": 1},
        )
    )
    total = 0.0
    stamped = 0
    by_method = dict(empty)
    for payment in docs:
        amount = round(float(payment.get("amount", 0) or 0), 2)
        if amount <= 0:
            continue
        key = (str(payment.get("booking_id") or ""), amount)
        if key in counted:
            continue
        total += amount
        stamped += 1
        method = str(payment.get("method") or "").lower()
        if method in ("cash", "efectivo"):
            by_method["cash"] = round(by_method["cash"] + amount, 2)
        elif method in ("card", "credit_card"):
            by_method["card"] = round(by_method["card"] + amount, 2)
        elif method in ("bank_transfer", "transfer", "transferencia"):
            by_method["transfer"] = round(by_method["transfer"] + amount, 2)
        else:
            by_method["other"] = round(by_method["other"] + amount, 2)
    return round(total, 2), stamped, by_method


def _stamped_drawer_addition(doc: dict) -> tuple[float, int]:
    """Backward-compatible wrapper: just the total + count."""
    total, stamped, _ = _stamped_drawer_breakdown(doc)
    return total, stamped


def list_open_shifts_overview() -> list[dict[str, Any]]:
    """Management overview of EVERY open shift across all hotels.

    A gerente/super_admin view to spot forgotten shifts: each row carries
    the hotel label, the configured shift label, age in hours
    (``hours_open``), the per-hotel ``max_open_hours`` limit and whether
    the shift is already past it (``is_expired``). ``total_collected`` is
    the UNIFIED drawer total: the shift's registered transactions plus the
    confirmed payments stamped with its ``shift_id`` (without double-
    counting the check-out settlement). Sorted by age descending.
    """
    db = get_database()
    docs = list(
        db[RECEPTION_SHIFTS_COLLECTION]
        .find({"status": "open"})
        .sort("start_time", 1)
    )
    now = _now_dt()
    hotel_cache: dict[int, str] = {}

    rows: list[dict[str, Any]] = []
    for doc in docs:
        prop_id = int(doc.get("prop_id") or 0)
        if prop_id and prop_id not in hotel_cache:
            hotel = db.dim_hotels.find_one(
                {"prop_id": prop_id},
                {"_id": 0, "display_name": 1, "hotel_name": 1},
            )
            hotel_cache[prop_id] = (
                (hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}")
                if hotel
                else f"Hotel {prop_id}"
            )

        config_doc = db[RECEPTION_SHIFT_CONFIG_COLLECTION].find_one({"prop_id": prop_id})
        max_open_hours = _max_open_hours_for_doc(config_doc)

        start_raw = doc.get("start_time")
        hours_open = 0.0
        expires_at: str | None = None
        try:
            start = datetime.fromisoformat(str(start_raw))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            hours_open = round(max((now - start).total_seconds() / 3600.0, 0.0), 2)
            expires_at = (start + timedelta(hours=max_open_hours)).isoformat()
        except (TypeError, ValueError):
            hours_open = 0.0

        shift_type = doc.get("shift_type", "morning")
        labels = get_shift_labels(prop_id)
        stamped_total, stamped_count, stamped_methods = _stamped_drawer_breakdown(doc)
        drawer_total = round(float(doc.get("total_collected") or 0) + stamped_total, 2)
        # Desglose por método del arqueo esperado: transacciones del turno
        # (por payment_method) + pagos estampados (por method), sin dedupe
        # cruzado porque los estampados ya excluyen la liquidación contada.
        txn_breakdown = _calc_payment_breakdown(doc.get("transactions") or [])
        payment_breakdown = {
            "cash": round(txn_breakdown["cash"] + stamped_methods["cash"], 2),
            "card": round(txn_breakdown["card"] + stamped_methods["card"], 2),
            "transfer": round(txn_breakdown["transfer"] + stamped_methods["transfer"], 2),
            "other": round(txn_breakdown["other"] + stamped_methods["other"], 2),
        }
        payment_breakdown["total"] = round(sum(payment_breakdown.values()), 2)
        rows.append(
            {
                "id": str(doc["_id"]),
                "prop_id": prop_id,
                "hotel_name": hotel_cache.get(prop_id, f"Hotel {prop_id}"),
                "shift_type": shift_type,
                "shift_label": labels.get(shift_type, shift_type),
                "employee": doc.get("employee") or "—",
                "opened_by": doc.get("opened_by"),
                "start_time": start_raw,
                "cash_initial": float(doc.get("cash_initial") or 0),
                # Drawer total unificado: transacciones del turno + pagos
                # estampados con shift_id (sin doble-contar el check-out).
                "total_collected": drawer_total,
                "stamped_payments_count": stamped_count,
                "payment_breakdown": payment_breakdown,
                "transaction_count": len(doc.get("transactions") or []),
                "hours_open": hours_open,
                "max_open_hours": max_open_hours,
                "is_expired": _shift_expired(start_raw, max_open_hours, now),
                "expires_at": expires_at,
            }
        )

    rows.sort(key=lambda r: r["hours_open"], reverse=True)
    return rows


def get_shift_attribution(shift_id: str | None) -> dict[str, Any] | None:
    """Employee/opener attribution of a shift, for stamping on money docs.

    Money-handling documents (payments, refunds, folio postings) carry the
    responsible cashier: the shift's visual ``employee`` label and the
    authenticated opener. Returns ``None`` when the shift cannot be resolved
    so callers can stamp ``shift_id`` alone without failing the write.
    """
    if not shift_id:
        return None
    try:
        doc = get_database()[RECEPTION_SHIFTS_COLLECTION].find_one(
            {"_id": ObjectId(shift_id)},
            {"employee": 1, "opened_by": 1, "opened_by_id": 1, "shift_type": 1},
        )
    except Exception:
        return None
    if not doc:
        return None
    return {
        "shift_employee": doc.get("employee"),
        "shift_opened_by": doc.get("opened_by"),
        "shift_opened_by_id": doc.get("opened_by_id"),
        "shift_type": doc.get("shift_type"),
    }


def get_active_shift(prop_id: int) -> dict[str, Any] | None:
    """Get the currently active (open) shift for a property.

    The returned payload carries the max-open control fields (``is_expired``,
    ``max_open_hours``, ``expires_at``) so the UI can alert when the shift
    has been open too long and cash operations are blocked.
    """
    db = get_database()
    doc = db[RECEPTION_SHIFTS_COLLECTION].find_one(
        {"prop_id": prop_id, "status": "open"},
    )
    if not doc:
        return None
    enriched = _enrich_shift(dict(doc))
    config_doc = db[RECEPTION_SHIFT_CONFIG_COLLECTION].find_one({"prop_id": prop_id})
    max_open_hours = _max_open_hours_for_doc(config_doc)
    now = _now_dt()
    enriched["max_open_hours"] = max_open_hours
    enriched["is_expired"] = _shift_expired(doc.get("start_time"), max_open_hours, now)
    try:
        start = datetime.fromisoformat(str(doc.get("start_time")))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        enriched["expires_at"] = (start + timedelta(hours=max_open_hours)).isoformat()
    except (TypeError, ValueError):
        enriched["expires_at"] = None
    return enriched


def get_active_shift_id(prop_id: int) -> str | None:
    """Return the ``_id`` (as string) of the active (open) shift for a property.

    Front-desk operations (check-in/check-out, cash payments, walk-ins) use
    this to (a) gate the operation with a 409 when no shift is open and
    (b) stamp the ``shift_id`` FK on the documents they create/update at write
    time — replacing the fragile time-window backfill in ``_collect_related_ids``,
    which guesses relationships at close time and can miss/over-capture records
    when timestamps drift across shift boundaries.

    Web-channel bookings (``booking_source`` not front-desk) never go through
    this helper, so they keep ``shift_id`` null.
    """
    db = get_database()
    doc = db[RECEPTION_SHIFTS_COLLECTION].find_one(
        {"prop_id": prop_id, "status": "open"},
        {"_id": 1},
    )
    if not doc:
        return None
    return str(doc["_id"])


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
    shifts = [_enrich_shift(d) for d in docs]
    # Manager view: resolve each shift's payments with their cashier
    # attribution so the UI can show a "Responsable" column per payment,
    # plus a per-employee summary of what each cashier collected (for
    # detecting discrepancies between stamped and deposited cash).
    for shift in shifts:
        shift["payments"] = _resolve_shift_payments(shift.get("payment_ids", []))
        shift["employee_summary"] = _shift_employee_summary(shift.get("id") or "")
    return shifts


def _resolve_shift_payments(payment_ids: list[Any]) -> list[dict[str, Any]]:
    """Resolve shift-stamped payments to compact wire entries.

    Returns the payment's own shift attribution (``shift_employee`` /
    ``shift_opened_by`` / ``shift_type`` — null for payments collected
    outside the cashier gate, e.g. web-channel) so the manager cash-control
    view can attribute every money movement to the responsible cashier.
    """
    if not payment_ids:
        return []
    db = get_database()
    docs = list(
        db.reservation_payments.find(
            {"_id": {"$in": payment_ids}},
            {
                "amount": 1,
                "method": 1,
                "reference": 1,
                "paid_at": 1,
                "shift_employee": 1,
                "shift_opened_by": 1,
                "shift_type": 1,
            },
        )
    )
    result: list[dict[str, Any]] = []
    for doc in docs:
        paid_at = doc.get("paid_at")
        if isinstance(paid_at, datetime):
            paid_at = paid_at.isoformat()
        result.append({
            "payment_id": str(doc.get("_id", "")),
            "amount": round(float(doc.get("amount", 0) or 0), 2),
            "method": doc.get("method", ""),
            "reference": doc.get("reference"),
            "paid_at": paid_at or "",
            "shift_employee": doc.get("shift_employee"),
            "shift_opened_by": doc.get("shift_opened_by"),
            "shift_type": doc.get("shift_type"),
        })
    result.sort(key=lambda p: p.get("paid_at", ""), reverse=True)
    return result


def _shift_employee_summary(shift_id: str) -> list[dict[str, Any]]:
    """Group the shift's stamped payments by responsible cashier.

    Uses the ``shift_id`` FK (payments stamped on THIS exact shift, confirmed
    only) as the source of truth for what was collected. Each payment is
    attributed to its denormalized ``shift_employee`` (falls back to
    ``shift_opened_by``); payments without any attribution group under
    "Sin atribución" so discrepancies between stamped and deposited cash
    are visible to the manager.
    """
    if not shift_id:
        return []
    try:
        shift_oid = ObjectId(shift_id)
    except Exception:
        return []
    db = get_database()
    docs = list(
        db.reservation_payments.find(
            {"shift_id": shift_oid, "status": "confirmed"},
            {"amount": 1, "method": 1, "shift_employee": 1, "shift_opened_by": 1},
        )
    )
    groups: dict[str, dict[str, Any]] = {}
    for doc in docs:
        employee = doc.get("shift_employee") or doc.get("shift_opened_by") or "Sin atribución"
        group = groups.setdefault(
            employee,
            {
                "employee": employee,
                "count": 0,
                "total": 0.0,
                "cash": 0.0,
                "card": 0.0,
                "transfer": 0.0,
                "other": 0.0,
            },
        )
        amount = round(float(doc.get("amount", 0) or 0), 2)
        group["count"] += 1
        group["total"] = round(group["total"] + amount, 2)
        method = str(doc.get("method") or "").lower()
        if method in ("cash", "efectivo"):
            group["cash"] = round(group["cash"] + amount, 2)
        elif method in ("card", "credit_card"):
            group["card"] = round(group["card"] + amount, 2)
        elif method in ("bank_transfer", "transfer", "transferencia"):
            group["transfer"] = round(group["transfer"] + amount, 2)
        else:
            group["other"] = round(group["other"] + amount, 2)
    return sorted(groups.values(), key=lambda g: g["total"], reverse=True)


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
