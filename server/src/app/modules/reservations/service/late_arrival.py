"""Llegada tardía / no-show — política configurable por hotel.

Contrato (política recomendada para HotelData — sprint llegada tardía/no-show):

- ``hotel_policies`` (fila hotel-wide, mismo scope que ``early_check_in_*``)
  define tres campos:
    ``guaranteed_reservation``  bool   — reserva garantizada (el auto no-show
                                          nunca la procesa; la decisión es humana).
    ``late_arrival_cutoff``     HH:MM  — hora límite de llegada el día del
                                          check-in (default ``23:59``).
    ``no_show_execution``       enum   — ``next_day`` (default): el auto job
                                          procesa a partir del día siguiente;
                                          ``same_day_cutoff``: también el mismo
                                          día una vez pasada la hora límite;
                                          ``manual``: nunca automático.
- Una reserva está ``protected_from_auto_no_show`` si su hotel tiene la
  reserva como garantizada, o si la llegada tardía fue declarada (flag
  ``declared_late_arrival``, marcador ``late_checkin`` o ``estimated_arrival_time``).
- La ventana de llegada tardía post-medianoche: una reserva cuyo check-in fue
  AYER sigue siendo checkeable mientras no sea no-show y el check-out no haya
  vencido. Más de un día de retraso = caso de gerente/no-show, no check-in normal.

Seam puro: todas las funciones reciben ``db`` (mismo patrón que el resto del
módulo reservations) para poder testearse contra la BD de test.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.app.core.timezone import local_today
from src.app.modules.reservations.notifications.guest import notify_guest_late_arrival

from ._helpers import utc_now

logger = logging.getLogger(__name__)

DEFAULT_LATE_ARRIVAL_CUTOFF = "23:59"
NO_SHOW_EXECUTION_DEFAULT = "next_day"
NO_SHOW_EXECUTION_OPTIONS = ("next_day", "same_day_cutoff", "manual")


def _parse_time_minutes(value: Any) -> int | None:
    """Validate HH:MM; return minutes since midnight or None if invalid."""
    raw = str(value or "").strip()
    parts = raw.split(":")
    if len(parts) < 2:
        return None
    try:
        hours, minutes = int(parts[0]), int(parts[1])
    except (TypeError, ValueError):
        return None
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return hours * 60 + minutes


def _normalize_policy_row(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw hotel_policies row (or empty dict) to the policy shape."""
    guaranteed = bool(row.get("guaranteed_reservation", False))

    cutoff = str(row.get("late_arrival_cutoff") or "").strip()
    if _parse_time_minutes(cutoff) is None:
        cutoff = DEFAULT_LATE_ARRIVAL_CUTOFF

    execution = str(row.get("no_show_execution") or "").strip().lower()
    if execution not in NO_SHOW_EXECUTION_OPTIONS:
        execution = NO_SHOW_EXECUTION_DEFAULT

    return {
        "guaranteed_reservation": guaranteed,
        "late_arrival_cutoff": cutoff,
        "no_show_execution": execution,
    }


_HOTEL_WIDE_FILTER = {
    "room_type_id": {"$in": ["", None]},
    "rate_plan_id": {"$in": ["", None]},
    "season_id": {"$in": ["", None]},
}
_POLICY_PROJECTION = {
    "prop_id": 1,
    "guaranteed_reservation": 1,
    "late_arrival_cutoff": 1,
    "no_show_execution": 1,
}


def resolve_late_arrival_policy(db: Any, prop_id: int) -> dict[str, Any]:
    """Resolve the hotel-wide late-arrival/no-show policy with defaults.

    Only the hotel-wide row (``room_type_id``/``rate_plan_id``/``season_id``
    empty) defines arrival policy — per-room-type rows must not silently
    override global hours (same contract as ``early_check_in_*``).
    """
    row = db.hotel_policies.find_one(
        {"prop_id": int(prop_id), **_HOTEL_WIDE_FILTER},
        _POLICY_PROJECTION,
    ) or {}
    return _normalize_policy_row(row)


def resolve_late_arrival_policies(
    db: Any,
    prop_ids: list[int],
) -> dict[int, dict[str, Any]]:
    """Bulk variant for jobs: one query for every requested prop_id.

    Returns a policy dict for EVERY prop_id (defaults when no hotel-wide row).
    """
    ids = [int(p) for p in prop_ids]
    result: dict[int, dict[str, Any]] = {pid: _normalize_policy_row({}) for pid in ids}
    if not ids:
        return result
    for row in db.hotel_policies.find({"prop_id": {"$in": ids}, **_HOTEL_WIDE_FILTER}, _POLICY_PROJECTION):
        result[int(row.get("prop_id", 0))] = _normalize_policy_row(row)
    return result


def protected_from_auto_no_show(
    booking: dict[str, Any],
    policy: dict[str, Any],
) -> bool:
    """True cuando el auto no-show NO debe procesar esta reserva.

    Protegen: reserva garantizada por política del hotel, flag explícito de
    llegada tardía declarada, o marcadores de llegada tardía del huésped
    (``late_checkin`` / ``estimated_arrival_time``).
    """
    if policy.get("guaranteed_reservation"):
        return True
    return _has_declared_late_arrival(booking)


def late_arrival_cutoff_reached(
    policy: dict[str, Any],
    *,
    now: Any = None,
) -> bool:
    """True cuando la hora local ya pasó la hora límite de llegada."""
    if now is None:
        from src.app.core.timezone import local_now
        now = local_now()
    cutoff_min = _parse_time_minutes(policy.get("late_arrival_cutoff"))
    if cutoff_min is None:
        return True
    return (now.hour * 60 + now.minute) >= cutoff_min


def _has_declared_late_arrival(booking: dict[str, Any]) -> bool:
    return bool(
        booking.get("declared_late_arrival")
        or booking.get("late_checkin")
        or str(booking.get("estimated_arrival_time") or "").strip()
    )


def get_late_arrival_context(db: Any, booking: dict[str, Any]) -> dict[str, Any]:
    """Read-only context for the check-in UI and the auto no-show job.

    ``blocked_reason`` is one of ``no_show`` | ``stay_ended`` | ``too_late``
    when the late-arrival window is closed, else ``None``.
    """
    policy = resolve_late_arrival_policy(db, int(booking.get("prop_id", 0) or 0))
    today = date.fromisoformat(local_today())

    check_in_str = str(booking.get("check_in_date") or "")[:10]
    try:
        check_in_date = date.fromisoformat(check_in_str)
    except ValueError:
        check_in_date = None

    stay_status = str(booking.get("stay_status") or "").strip().lower()
    check_out_str = str(booking.get("check_out_date") or "")[:10]
    check_out_passed = False
    if check_out_str:
        try:
            check_out_passed = date.fromisoformat(check_out_str) < today
        except ValueError:
            pass

    declared = bool(booking.get("declared_late_arrival", False))
    protected = protected_from_auto_no_show(booking, policy)

    days_ago: int | None = None
    is_window = False
    blocked_reason: str | None = None
    if check_in_date is not None:
        days_ago = (today - check_in_date).days
        if stay_status == "no_show":
            blocked_reason = "no_show"
        elif check_out_passed:
            blocked_reason = "stay_ended"
        elif days_ago > 1:
            blocked_reason = "too_late"
        elif days_ago == 1:
            is_window = True

    return {
        "guaranteed_reservation": policy["guaranteed_reservation"],
        "late_arrival_cutoff": policy["late_arrival_cutoff"],
        "no_show_execution": policy["no_show_execution"],
        "declared_late_arrival": declared,
        "protected_from_auto_no_show": protected,
        "is_late_arrival_window": is_window,
        "check_in_days_ago": days_ago,
        "blocked_reason": blocked_reason,
    }


def declare_late_arrival(
    db: Any,
    booking_id: str,
    *,
    declared: bool,
    estimated_arrival_time: str | None = None,
    changed_by: str = "web",
) -> dict[str, Any]:
    """Recepción declara (o retira) una llegada tardía para una reserva.

    El flag ``declared_late_arrival`` protege la reserva del auto no-show y
    actualiza (opcionalmente) la hora estimada de llegada. El check-in normal
    queda intacto; la declaración es solo señal operativa + protección.
    """
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "_id": 0,
            "status": 1,
            "stay_status": 1,
            "is_test": 1,
            "prop_id": 1,
            "guest_name": 1,
            "guest_email": 1,
            "check_in_date": 1,
            "check_out_date": 1,
            "total_nights": 1,
        },
    )
    if not booking:
        raise ValueError("Reserva no encontrada.")
    if booking.get("status") in ("cancelled", "rejected"):
        raise ValueError(
            "No se puede declarar llegada tardía en una reserva cancelada o rechazada. "
            "Creá una reserva nueva o contactá al equipo."
        )
    if str(booking.get("stay_status") or "").strip().lower() == "no_show":
        raise ValueError(
            "La reserva fue marcada como no-show; no se puede declarar llegada tardía. "
            "Pedí al gerente que la reabra (hoy o ayer con estadía vigente) "
            "o creá una reserva nueva."
        )

    eta = ""
    if estimated_arrival_time is not None:
        raw = str(estimated_arrival_time or "").strip()
        if raw and _parse_time_minutes(raw) is None:
            raise ValueError("La hora estimada de llegada debe tener formato HH:MM (ej. 01:30).")
        eta = raw

    set_fields: dict[str, Any] = {
        "declared_late_arrival": bool(declared),
        "updated_at": utc_now(),
    }
    if estimated_arrival_time is not None:
        set_fields["estimated_arrival_time"] = eta

    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": set_fields})

    # Notificar al huésped SOLO al declarar (no al retirar), con email real y
    # fuera de datos de prueba — reutiliza el pipeline de notification_log.
    if declared and not booking.get("is_test"):
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email:
                notify_guest_late_arrival(
                    booking_id=booking_id,
                    guest_name=booking.get("guest_name", ""),
                    guest_email=guest_email,
                    prop_id=int(booking.get("prop_id", 0)),
                    check_in_date=str(booking.get("check_in_date", "")),
                    check_out_date=str(booking.get("check_out_date", "")),
                    total_nights=int(booking.get("total_nights", 0) or 0),
                    estimated_arrival_time=eta,
                )
        except Exception:
            logger.exception("Failed to notify guest of late arrival for booking %s", booking_id)

    state = "declarada" if declared else "retirada"
    reason_parts = [f"llegada tardía {state}"]
    if eta:
        reason_parts.append(f"hora estimada {eta}")
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "unknown"),
        "changed_at": utc_now(),
        "reason": f"check_in_late_arrival: {', '.join(reason_parts)}",
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test")),
    })

    return {
        "booking_id": booking_id,
        "declared_late_arrival": bool(declared),
        "estimated_arrival_time": eta,
    }
