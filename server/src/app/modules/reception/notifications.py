"""Internal notifications for forgotten open cash shifts.

A periodic sweep (daemon thread started in ``main.py`` lifespan) writes
rows to ``notification_log`` — the same collection that feeds the bell
(``/api/notifications/my``) — for every open shift that:

- has exceeded the hotel's ``max_open_hours`` (``shift_expired``): the
  cash-drawer block is active and a manager must close the shift; and
- has been open at least ``notify_manager_hours`` (``shift_open_long``):
  a heads-up to the hotel manager before the block kicks in.

Recipients: active ``gerente_hotel`` users assigned to the property plus
``super_admin``. Rows use ``status="sent"`` so they count as unread in the
bell. Best-effort by design — a notification failure never breaks the
sweep. Deduplication is enforced by a unique index on
``shift_notification_dedup`` (``shift_id`` + ``notification_type``), so a
5-minute sweep never spams.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from src.app.security.role_helpers import build_role_query, get_role_name
from src.database.connection import get_database

from .collections import (
    RECEPTION_SHIFT_CONFIG_COLLECTION,
    RECEPTION_SHIFTS_COLLECTION,
    SHIFT_NOTIFICATION_DEDUP_COLLECTION,
)
from .shifts import (
    DEFAULT_MAX_OPEN_HOURS,
    DEFAULT_NOTIFY_MANAGER_HOURS,
    _max_open_hours_for_doc,
    _notify_manager_hours_for_doc,
    _now_dt,
    _shift_expired,
)

logger = logging.getLogger(__name__)

# Manager targets for shift alerts: hotel managers (scoped by assigned
# hotels) + super admins (oversee the whole chain).
MANAGER_ROLES = ("gerente_hotel",)
CHAIN_ADMIN_ROLES = ("super_admin",)

# How often the daemon sweep runs (seconds).
SWEEP_INTERVAL_SECONDS = 300

NOTIFICATION_TYPE_EXPIRED = "shift_expired"
NOTIFICATION_TYPE_OPEN_LONG = "shift_open_long"


def _resolve_manager_recipients(prop_id: int) -> list[dict[str, str]]:
    """Active manager emails for ``prop_id`` (gerente_hotel + super_admin)."""
    db = get_database()
    candidates = list(
        db.users.find(
            {
                **build_role_query(list(MANAGER_ROLES) + list(CHAIN_ADMIN_ROLES)),
                "is_active": True,
            },
            {
                "_id": 0,
                "username": 1,
                "display_name": 1,
                "email": 1,
                "primary_role_id": 1,
                "primary_role": 1,
                "assigned_hotels": 1,
            },
        )
    )

    recipients: list[dict[str, str]] = []
    for user in candidates:
        role = get_role_name(user)
        email = (user.get("email") or "").strip()
        if not email:
            continue
        if role in CHAIN_ADMIN_ROLES:
            recipients.append(
                {
                    "email": email,
                    "name": user.get("display_name") or user.get("username") or "Administrador",
                }
            )
            continue
        assigned = user.get("assigned_hotels", [])
        if not isinstance(assigned, list):
            continue
        try:
            int_ids = {int(p) for p in assigned if p is not None}
        except (ValueError, TypeError):
            continue
        if prop_id in int_ids:
            recipients.append(
                {
                    "email": email,
                    "name": user.get("display_name") or user.get("username") or "Gerente",
                }
            )
    return recipients


def _hotel_label(prop_id: int) -> str:
    db = get_database()
    hotel = db.dim_hotels.find_one(
        {"prop_id": prop_id},
        {"_id": 0, "display_name": 1, "hotel_name": 1},
    )
    return (
        (hotel or {}).get("display_name")
        or (hotel or {}).get("hotel_name")
        or f"Propiedad #{prop_id}"
    )


def _insert_notification_rows(
    *,
    notification_type: str,
    prop_id: int,
    shift_id: str,
    message: str,
    extra: dict[str, Any],
) -> None:
    """Best-effort write of bell rows for every manager recipient."""
    recipients = _resolve_manager_recipients(prop_id)
    if not recipients:
        logger.info(
            "No manager recipients for %s prop_id=%s shift=%s",
            notification_type, prop_id, shift_id,
        )
        return
    db = get_database()
    now = datetime.now(timezone.utc)
    for recipient in recipients:
        try:
            db.notification_log.insert_one(
                {
                    "notification_type": notification_type,
                    "recipient_email": recipient["email"],
                    "recipient_name": recipient["name"],
                    "prop_id": prop_id,
                    "shift_id": shift_id,
                    "status": "sent",  # unread in the bell
                    "message": message,
                    "metadata": extra,
                    "created_at": now,
                }
            )
        except Exception:
            logger.exception(
                "Failed to write %s notification for %s (prop_id=%s shift=%s)",
                notification_type, recipient["email"], prop_id, shift_id,
            )


def _mark_notified(shift_id: str, notification_type: str) -> bool:
    """Atomically claim the (shift_id, type) notification slot.

    Returns True when this sweep wins the slot (i.e. the notification has
    not been sent yet); False when a previous sweep already sent it.
    """
    db = get_database()
    try:
        db[SHIFT_NOTIFICATION_DEDUP_COLLECTION].insert_one(
            {
                "shift_id": shift_id,
                "notification_type": notification_type,
                "created_at": datetime.now(timezone.utc),
            }
        )
        return True
    except Exception:
        # DuplicateKeyError (already notified) or transient mongo blip.
        # Either way: do not double-notify.
        return False


def _hours_open(start_time: Any, now: datetime) -> float | None:
    if not start_time:
        return None
    try:
        start = datetime.fromisoformat(str(start_time))
    except (TypeError, ValueError):
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return max(0.0, (now - start).total_seconds() / 3600)


def sweep_shift_notifications() -> int:
    """Scan every open shift and notify managers about expired / long-open.

    Returns the number of notification rows written (dedup already applied).
    Idempotent: a second sweep produces no new rows.
    """
    db = get_database()
    now = _now_dt()
    written = 0

    for shift in db[RECEPTION_SHIFTS_COLLECTION].find({"status": "open"}):
        prop_id = int(shift.get("prop_id") or 0)
        shift_id = str(shift["_id"])
        config_doc = db[RECEPTION_SHIFT_CONFIG_COLLECTION].find_one({"prop_id": prop_id})
        max_open_hours = _max_open_hours_for_doc(config_doc)
        notify_hours = _notify_manager_hours_for_doc(config_doc)
        hours = _hours_open(shift.get("start_time"), now)

        # 1) Expired → cash operations are blocked; manager must close.
        if _shift_expired(shift.get("start_time"), max_open_hours, now):
            if _mark_notified(shift_id, NOTIFICATION_TYPE_EXPIRED):
                _insert_notification_rows(
                    notification_type=NOTIFICATION_TYPE_EXPIRED,
                    prop_id=prop_id,
                    shift_id=shift_id,
                    message=(
                        f"El turno de {_hotel_label(prop_id)} lleva más de "
                        f"{max_open_hours:g} horas sin cerrarse (abierto el "
                        f"{shift.get('start_time')}). Las operaciones de caja "
                        f"están bloqueadas — ciérralo desde Cajas y Turnos."
                    ),
                    extra={
                        "shift_id": shift_id,
                        "prop_id": prop_id,
                        "max_open_hours": max_open_hours,
                        "hours_open": round(hours, 2) if hours is not None else None,
                    },
                )
                written += 1

        # 2) Open too long → heads-up to the manager before the block.
        if hours is not None and hours >= notify_hours:
            if _mark_notified(shift_id, NOTIFICATION_TYPE_OPEN_LONG):
                _insert_notification_rows(
                    notification_type=NOTIFICATION_TYPE_OPEN_LONG,
                    prop_id=prop_id,
                    shift_id=shift_id,
                    message=(
                        f"El turno de {_hotel_label(prop_id)} lleva "
                        f"{hours:.0f} horas sin cerrarse (aviso configurado a "
                        f"{notify_hours:g}h). Revisa quién debe cerrarlo antes "
                        f"de que se bloqueen las operaciones de caja."
                    ),
                    extra={
                        "shift_id": shift_id,
                        "prop_id": prop_id,
                        "notify_manager_hours": notify_hours,
                        "hours_open": round(hours, 2),
                    },
                )
                written += 1

    return written


def sweep_shift_notifications_forever(*, interval_seconds: int = SWEEP_INTERVAL_SECONDS) -> None:
    """Daemon-thread loop for the shift notification sweep.

    Runs once immediately, then sleeps ``interval_seconds`` between sweeps.
    Interruptible via threading.Event so SIGTERM tears down cleanly.
    """

    def worker() -> None:
        logger.info("Starting shift-notification sweep (interval=%ss)", interval_seconds)
        while True:
            try:
                sent = sweep_shift_notifications()
                if sent:
                    logger.info("Shift sweep wrote %d notification(s)", sent)
            except Exception:
                logger.exception("Shift-notification sweep failed; will retry on next interval")
            threading.Event().wait(interval_seconds)

    t = threading.Thread(target=worker, daemon=True, name="ShiftNotificationSweep")
    t.start()
