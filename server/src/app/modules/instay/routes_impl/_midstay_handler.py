"""Mid-stay operations triggered by service request completion.

- extend_stay: extend the booking's check-out date, post additional room charge
- early_checkout: process understay with penalty, restore unused inventory

Integrated into the existing instay module — called from routes.py when staff
completes a service request of type extend_stay or early_checkout.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from src.database.connection import get_database

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _room_rate_per_night(booking: dict) -> float:
    """Calculate the room rate per night from the booking."""
    total_price = float(booking.get("total_price", 0) or 0)
    total_nights = int(booking.get("total_nights", 1)) or 1
    return round(total_price / total_nights, 2)


# ── Extend Stay ─────────────────────────────────────────────────


def process_extend_stay(
    booking_id: str,
    *,
    new_check_out_date: str,
    changed_by: str = "staff",
) -> dict[str, Any]:
    """Extend the guest's stay by updating the check-out date.

    Validates that the new date is after the current check-out date,
    calculates additional nights and room charge, posts to folio,
    and updates the booking.

    Returns {"ok": True, "extra_nights": N, "additional_charge": X.XX}
    or raises ValueError with a user-facing message.
    """
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id, "stay_status": "checked_in"},
    )
    if not booking:
        raise ValueError("Reserva no encontrada o no está en estancia activa.")

    old_check_out = str(booking.get("check_out_date", ""))[:10]
    try:
        new_co = date.fromisoformat(new_check_out_date)
        old_co = date.fromisoformat(old_check_out) if old_check_out else date.today()
    except ValueError:
        raise ValueError(f"Fecha inválida: {new_check_out_date}. Use formato YYYY-MM-DD.")

    if new_co <= old_co:
        raise ValueError(
            f"La nueva fecha de salida ({new_check_out_date}) debe ser posterior "
            f"a la fecha actual ({old_check_out})."
        )

    extra_nights = (new_co - old_co).days
    if extra_nights <= 0:
        raise ValueError("La extensión debe ser de al menos 1 noche adicional.")

    rate_per_night = _room_rate_per_night(booking)
    additional_charge = round(rate_per_night * extra_nights, 2)

    now = _now()

    # Update booking
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "check_out_date": new_check_out_date,
                "total_nights": int(booking.get("total_nights", 1)) + extra_nights,
                "updated_at": now,
            }
        },
    )

    # Post additional room charge to folio
    try:
        from src.app.modules.billing.service.folio import post_to_folio
        post_to_folio(
            booking_id,
            posting_type="charge",
            category="Habitación",
            concept=f"Extensión de estancia — {extra_nights} noche(s) adicional(es)",
            amount=additional_charge,
            quantity=extra_nights,
            reference_id=booking_id,
            reference_type="extend_stay",
        )
    except Exception:
        logger.exception("Failed to post extend_stay charge to folio for %s", booking_id)

    # Log in history
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "extended_stay",
        "changed_at": now,
        "reason": (
            f"Estancia extendida {extra_nights} noche(s) — "
            f"{old_check_out} → {new_check_out_date} — "
            f"Cargo adicional: ${additional_charge}"
        ),
        "changed_by": changed_by,
        "is_test": False,
    })

    # Update stay session expiry
    try:
        from src.app.modules.instay.routes_impl._helpers import session_expiry
        db.stay_sessions.update_one(
            {"booking_id": booking_id, "active": True},
            {"$set": {"check_out": new_check_out_date, "expires_at": session_expiry()}},
        )
    except Exception:
        logger.exception("Failed to extend stay session for %s", booking_id)

    logger.info(
        "Stay extended for booking %s: +%d nights, +$%.2f",
        booking_id, extra_nights, additional_charge,
    )

    return {
        "ok": True,
        "extra_nights": extra_nights,
        "additional_charge": additional_charge,
        "new_check_out_date": new_check_out_date,
    }


# ── Early Check-Out ────────────────────────────────────────────


def process_early_checkout(
    booking_id: str,
    *,
    changed_by: str = "staff",
) -> dict[str, Any]:
    """Process an early check-out (understay) with penalty.

    Reads the cancellation_penalty_percent from hotel_policies (hierarchy:
    rate_plan > room_type > hotel-wide, default 100%). Calculates the
    penalty on remaining nights, posts to folio, updates booking, restores
    inventory, marks rooms dirty, creates cleaning tasks, and closes folio.

    Returns {"ok": True, "remaining_nights": N, "penalty_amount": X.XX}
    or raises ValueError.
    """
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id, "stay_status": "checked_in"},
    )
    if not booking:
        raise ValueError("Reserva no encontrada o no está en estancia activa.")

    check_out_str = str(booking.get("check_out_date", ""))[:10]
    try:
        check_out_date = date.fromisoformat(check_out_str)
    except ValueError:
        raise ValueError(f"Fecha de salida inválida en la reserva: {check_out_str}")

    today = date.today()
    remaining_nights = (check_out_date - today).days
    if remaining_nights <= 0:
        raise ValueError(
            f"No hay noches restantes para aplicar salida anticipada "
            f"(check-out: {check_out_str}, hoy: {today})."
        )

    # Resolve penalty percent from hotel_policies (hierarchy: rate_plan > room_type > hotel-wide)
    from src.app.modules.reservations.service.cleanup import resolve_penalty_percent
    penalty_pct = resolve_penalty_percent(
        prop_id=int(booking.get("prop_id", 0)),
        room_type_id=str(booking.get("room_type_id", "")),
        rate_plan_id=str(booking.get("rate_plan_id", "")),
    )

    rate_per_night = _room_rate_per_night(booking)
    remaining_value = round(rate_per_night * remaining_nights, 2)
    penalty_amount = round(remaining_value * penalty_pct / 100, 2)

    now = _now()
    actual_checkout = today.strftime("%Y-%m-%d")

    # Update booking
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "stay_status": "checked_out",
                "check_out_date_actual": actual_checkout,
                "check_out_time_actual": now.strftime("%H:%M"),
                "check_out_by": changed_by,
                "check_out_early_checkout": True,
                "check_out_early_penalty": penalty_amount,
                "check_out_early_remaining_nights": remaining_nights,
                "check_out_early_penalty_percent": penalty_pct,
                "updated_at": now,
            }
        },
    )

    # Restore inventory for unused nights
    try:
        from src.app.modules.reservations.service._transitions import _restore_inventory
        _restore_inventory(
            prop_id=int(booking.get("prop_id", 0)),
            check_in_date=str(booking.get("check_in_date", "")),
            check_out_date=str(booking.get("check_out_date", "")),
            rooms=int(booking.get("rooms", 1)),
            room_type_id=str(booking.get("room_type_id", "")),
        )
    except Exception:
        logger.exception("Failed to restore inventory for early checkout %s", booking_id)

    # Post penalty to folio
    try:
        from src.app.modules.billing.service.folio import post_to_folio
        post_to_folio(
            booking_id,
            posting_type="charge",
            category="Penalización",
            concept=(
                f"Salida anticipada — Penalización del {penalty_pct:.0f}% "
                f"sobre {remaining_nights} noche(s) restante(s)"
            ),
            amount=penalty_amount,
            quantity=1,
            reference_id=booking_id,
            reference_type="early_checkout_penalty",
        )
    except Exception:
        logger.exception("Failed to post early_checkout penalty to folio for %s", booking_id)

    # Log in history
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "early_checkout",
        "changed_at": now,
        "reason": (
            f"Salida anticipada — {remaining_nights} noche(s) restante(s) — "
            f"Penalización del {penalty_pct:.0f}%: ${penalty_amount}"
        ),
        "changed_by": changed_by,
        "is_test": False,
    })

    # Deactivate stay session
    try:
        db.stay_sessions.update_many(
            {"booking_id": booking_id, "active": True},
            {"$set": {"active": False, "deactivated_at": now}},
        )
    except Exception:
        logger.exception("Failed to deactivate stay session for %s", booking_id)

    # Settle additional charges
    try:
        from src.app.modules.billing.service import update_invoice_additional_charges
        update_invoice_additional_charges(booking_id, changed_by=changed_by)
    except Exception:
        logger.exception("Failed to settle charges on early checkout %s", booking_id)

    # Mark rooms as dirty + create cleaning tasks
    try:
        assigned_rooms: list[str] = booking.get("assigned_rooms") or []
        prop_id = int(booking.get("prop_id", 0))
        if assigned_rooms:
            room_docs = list(
                db.hotel_rooms.find(
                    {"hotel_room_id": {"$in": assigned_rooms}},
                    {"_id": 0, "hotel_room_id": 1, "room_label": 1, "room_number": 1, "room_type_id": 1},
                )
            )
            for r in room_docs:
                label = r.get("room_label", "") or r.get("room_number", "")
                if not label:
                    continue
                db.room_status_log.update_one(
                    {"prop_id": prop_id, "room_label": label},
                    {"$set": {"status": "vacant_dirty", "note": f"Early check-out: {booking_id}", "updated_at": now},
                     "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
                db.housekeeping_tasks.insert_one({
                    "prop_id": prop_id,
                    "room_id": r.get("hotel_room_id", ""),
                    "room_label": label,
                    "room_number": r.get("room_number", ""),
                    "room_type_id": r.get("room_type_id", ""),
                    "task_type": "cleaning",
                    "status": "pending",
                    "assigned_to": "",
                    "priority": "normal",
                    "note": f"Limpieza automática post early check-out — reserva {booking_id}",
                    "scheduled_date": "",
                    "created_at": now,
                    "completed_at": None,
                })
            logger.info("Rooms marked as dirty + cleaning tasks for early checkout %s", booking_id)
    except Exception:
        logger.exception("Failed to mark rooms dirty for early checkout %s", booking_id)

    # Close folio
    try:
        from src.app.modules.billing.service.folio import close_folio
        close_folio(booking_id, closed_by=changed_by)
    except Exception:
        logger.exception("Failed to close folio on early checkout %s", booking_id)

    logger.info(
        "Early checkout for booking %s: %d remaining nights, $%.2f penalty",
        booking_id, remaining_nights, penalty_amount,
    )

    return {
        "ok": True,
        "remaining_nights": remaining_nights,
        "penalty_amount": penalty_amount,
        "actual_checkout": actual_checkout,
    }
