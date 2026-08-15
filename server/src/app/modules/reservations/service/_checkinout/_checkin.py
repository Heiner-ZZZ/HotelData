"""Check-in operations."""

from __future__ import annotations

import logging
import threading
from datetime import date, datetime
from typing import Any

from bson import ObjectId

from src.app.core.state_machine import (
    CHECKIN_ALLOWED_ROOM_STATUSES,
    CHECKIN_REJECTED_ROOM_STATUSES,
)
from src.app.core.timezone import local_now, local_today
from src.app.modules.partner.services.audit import register_action
from src.app.modules.reservations.service._checkinout._helpers import (
    _generate_folio,
    _notify_guest_check_in,
    _notify_staff_check_in,
    _notify_staff_window_extension,
)
from src.database.connection import get_database

from .._helpers import utc_now

logger = logging.getLogger(__name__)


_EARLY_CHECK_IN_MODES = {"early_courtesy", "early_approved"}


def _parse_time_minutes(value: Any) -> int | None:
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


def _policy_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def get_early_check_in_context(
    prop_id: int,
    check_in_date: str,
    *,
    now: datetime | None = None,
    db: Any | None = None,
) -> dict[str, Any]:
    """Resolve the server-authoritative early check-in state for a booking.

    This is deliberately read-only. It compares the hotel's configured
    check-in time with the current local time only when the reservation starts
    today; it never changes reservation dates or inventory.
    """
    database = db if db is not None else get_database()
    policy = database.hotel_policies.find_one(
        {
            "prop_id": prop_id,
            "room_type_id": {"$in": ["", None]},
            "rate_plan_id": {"$in": ["", None]},
            "season_id": {"$in": ["", None]},
        },
        {
            "_id": 0,
            "check_in_time": 1,
            "early_check_in_enabled": 1,
            "early_check_in_courtesy_minutes": 1,
            "early_check_in_default_fee": 1,
        },
    ) or {}

    check_in_time = str(policy.get("check_in_time") or "").strip()
    schedule_minutes = _parse_time_minutes(check_in_time)
    try:
        courtesy_minutes = max(0, min(int(policy.get("early_check_in_courtesy_minutes", 60) or 60), 240))
    except (TypeError, ValueError):
        courtesy_minutes = 60
    try:
        default_fee = max(0.0, round(float(policy.get("early_check_in_default_fee", 0) or 0), 2))
    except (TypeError, ValueError):
        default_fee = 0.0

    current = now or local_now()
    current_date = current.strftime("%Y-%m-%d")
    context: dict[str, Any] = {
        "enabled": _policy_bool(policy.get("early_check_in_enabled"), True),
        "is_early": False,
        "minutes_before": 0,
        "courtesy_minutes": courtesy_minutes,
        "requires_approval": False,
        "check_in_time": check_in_time,
        "default_fee": default_fee,
    }
    if schedule_minutes is None or not check_in_date or check_in_date != current_date:
        return context

    current_minutes = current.hour * 60 + current.minute
    minutes_before = schedule_minutes - current_minutes
    if minutes_before <= 0:
        return context

    context["is_early"] = True
    context["minutes_before"] = minutes_before
    context["requires_approval"] = minutes_before > courtesy_minutes
    return context


def validate_early_check_in(
    context: dict[str, Any],
    *,
    mode: str | None,
    approved: bool,
    reason: str,
    fee: Any,
) -> tuple[str | None, float, str]:
    """Validate an explicit early-arrival decision before any state write."""
    normalized_mode = str(mode or "").strip().lower() or None
    normalized_reason = str(reason or "").strip()
    if not context["is_early"]:
        if normalized_mode in _EARLY_CHECK_IN_MODES:
            raise ValueError(
                "La reserva ya está dentro del horario normal de check-in. "
                "Hacé el check-in normal, sin early check-in."
            )
        return None, 0.0, ""

    if not context["enabled"]:
        raise ValueError(
            "El early check-in está deshabilitado para este hotel. "
            "Hacé el check-in normal o contactá a gerencia si la llegada anticipada "
            "debería estar habilitada."
        )
    if normalized_mode not in _EARLY_CHECK_IN_MODES or not approved:
        raise ValueError(
            "El early check-in requiere una autorización explícita. "
            "Marca la autorización del gerente para continuar."
        )
    if context["requires_approval"] and normalized_mode != "early_approved":
        raise ValueError(
            "Este early check-in requiere aprobación del gerente por estar fuera de la cortesía. "
            "Contactá a gerencia para autorizar la llegada anticipada."
        )
    if normalized_mode == "early_approved" and context["requires_approval"] and not normalized_reason:
        raise ValueError("La aprobación de early check-in requiere un motivo.")

    try:
        normalized_fee = round(float(fee or 0), 2)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "El cargo de early check-in no es válido. "
            "Verificá el cargo de early check-in en la política del hotel."
        ) from exc
    if normalized_fee < 0:
        raise ValueError(
            "El cargo de early check-in no puede ser negativo. "
            "Verificá el cargo de early check-in en la política del hotel."
        )
    return normalized_mode, normalized_fee, normalized_reason


def update_check_in_datetime(
    booking_id: str,
    *,
    check_in_date: str | None = None,
    check_in_time: str | None = None,
    changed_by: str = "web",
) -> dict[str, Any]:
    """Update check-in date and/or time for an active booking."""
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "status": 1, "stay_status": 1, "is_test": 1},
    )
    if not booking:
        raise ValueError("Booking not found")
    if booking.get("status") in ("cancelled", "rejected"):
        raise ValueError(
            "No se puede modificar el check-in de una reserva cancelada o rechazada. "
            "Creá una reserva nueva o contactá al equipo."
        )

    now = utc_now()
    update_fields: dict[str, Any] = {"updated_at": now}
    reason_parts = []
    if check_in_date is not None:
        update_fields["check_in_date"] = check_in_date
        reason_parts.append(f"fecha: {check_in_date}")
    if check_in_time is not None:
        update_fields["check_in_time"] = check_in_time
        reason_parts.append(f"hora: {check_in_time}")

    if len(update_fields) == 1:
        return {"booking_id": booking_id, "updated": False, "detail": "No changes provided"}

    db.booking_orders.update_one({"booking_id": booking_id}, {"$set": update_fields})
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "unknown"),
        "changed_at": now,
        "reason": f"check-in actualizado: {', '.join(reason_parts)}",
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test", False)),
    })
    return {"booking_id": booking_id, "updated": True}


def complete_check_in(
    booking_id: str,
    *,
    changed_by: str = "web",
    payment_method: str = "",
    ip_address: str = "",
    observations: str = "",
    shift_id: str | None = None,
    early_check_in_mode: str | None = None,
    early_check_in_approved: bool = False,
    early_check_in_reason: str = "",
    early_check_in_fee: Any = 0,
    early_check_in_authorized: bool = False,
) -> dict[str, Any]:
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1, "is_test": 1,
         "check_in_date": 1, "check_out_date": 1, "total_price": 1, "currency": 1, "total_nights": 1,
         "assigned_rooms": 1, "stay_status": 1, "no_show_processed_at": 1,
         "room_type_id": 1, "rooms": 1, "no_show_reopened_at": 1, "inventory_re_deducted_at": 1},
    )
    if not booking:
        raise ValueError("Reserva no encontrada. Verificá el identificador de la reserva.")

    # ── Validate no-show: guest never arrived ──
    # Práctica hotelera: una reserva marcada como no-show (estado terminal) o
    # cuya estadía ya terminó sin que el huésped llegara no admite check-in.
    stay_status = str(booking.get("stay_status") or "").strip().lower()
    if stay_status == "no_show":
        raise ValueError(
            f"No se puede realizar el check-in: la reserva {booking_id} fue marcada como no-show. "
            "El huésped nunca llegó y la estancia quedó cerrada. "
            "Pedile al gerente que reabra la reserva (solo hoy o ayer con estadía vigente), "
            "ajustá las fechas o creá una reserva nueva."
        )

    check_out_date_str = booking.get("check_out_date", "")
    if check_out_date_str:
        try:
            co_date = date.fromisoformat(check_out_date_str)
            today = date.fromisoformat(local_today())
            if co_date < today:
                raise ValueError(
                    f"No se puede realizar el check-in: la reserva venció como no-show. "
                    f"La fecha de check-out ({check_out_date_str}) ya pasó (hoy {today.isoformat()}) "
                    "y el huésped nunca llegó a la propiedad. "
                    "Creá una reserva nueva con las fechas correctas."
                )
        except ValueError as exc:
            if str(exc).startswith("No se puede"):
                raise
            logger.warning("Could not parse check_out_date '%s' for booking %s", check_out_date_str, booking_id)

    # ── Validate check-in date (past / today / future) ──
    # Llegada tardía post-medianoche: una reserva cuyo check-in fue AYER sigue
    # siendo checkeable como ``late_arrival`` mientras no sea no-show y el
    # check-out no haya vencido (guard de arriba). Las fechas NO se mueven:
    # ``check_in_date`` conserva el día reservado y ``check_in_date_actual``
    # registra el día real. Más de un día de retraso = caso de no-show/gerente,
    # nunca check-in normal.
    is_late_arrival = False
    check_in_date_str = booking.get("check_in_date", "")
    if check_in_date_str:
        try:
            ci_date = date.fromisoformat(check_in_date_str)
            today = date.fromisoformat(local_today())
            if ci_date < today:
                days_late = (today - ci_date).days
                if days_late == 1:
                    is_late_arrival = True
                else:
                    raise ValueError(
                        f"No se puede realizar el check-in: la reserva venció como no-show. "
                        f"La fecha de check-in ({check_in_date_str}) es de hace {days_late} día(s); "
                        "ajustá las fechas o creá una reserva nueva."
                    )
            if ci_date > today:
                raise ValueError(
                    f"No se puede realizar check-in antes de la fecha de llegada. "
                    f"La fecha de check-in ({check_in_date_str}) es futura; hoy es {today.isoformat()}. "
                    "Esperá a la fecha de llegada o ajustá las fechas de la reserva."
                )
        except ValueError as exc:
            if str(exc).startswith("No se puede"):
                raise
            logger.warning("Could not parse check_in_date '%s' for booking %s", check_in_date_str, booking_id)

    # Capture one local clock snapshot for the policy decision, the persisted
    # actual arrival, and the early-arrival notification. Reading the clock
    # twice can cross a minute boundary and leave e.g. 30 minutes in the
    # policy but 14:31 in ``check_in_time_actual``.
    actual_arrival_at = local_now()
    early_context = get_early_check_in_context(
        int(booking.get("prop_id", 0) or 0),
        check_in_date_str,
        now=actual_arrival_at,
        db=db,
    )
    if (
        str(early_check_in_mode or "").strip().lower() == "early_approved"
        and not early_check_in_authorized
    ):
        raise ValueError(
            "Permiso requerido: check-ins.early_approve. "
            "Solo un gerente de hotel o super_admin puede aprobar este early check-in."
        )
    early_mode, early_fee, early_reason = validate_early_check_in(
        early_context,
        mode=early_check_in_mode,
        approved=early_check_in_approved,
        reason=early_check_in_reason,
        fee=early_check_in_fee,
    )

    # ── Reabierta sin re-deducción: red de seguridad de inventario ──
    # ``reopen_no_show`` ya re-deduce las noches y marca
    # ``inventory_re_deducted_at``. Este refuerzo cubre reservas reabiertas
    # ANTES de ese endurecimiento (o rutas que lo saltaron): si la marca no
    # está, se revalida y re-deduce aquí antes del check-in. Las reservas
    # normales (nunca no-show) ya tienen su inventario desde la confirmación.
    # Sin ``room_type_id`` no hay inventario nocturno que gestionar.
    if booking.get("no_show_reopened_at") and not booking.get("inventory_re_deducted_at"):
        room_type_id_ci = str(booking.get("room_type_id", "") or "")
        if room_type_id_ci:
            try:
                from src.app.modules.reservations.service._transitions import (
                    _deduct_inventory,
                )
                _deduct_inventory(
                    prop_id=int(booking.get("prop_id", 0) or 0),
                    check_in_date=str(booking.get("check_in_date", "") or ""),
                    check_out_date=str(booking.get("check_out_date", "") or ""),
                    rooms=int(booking.get("rooms", 1) or 1),
                    room_type_id=room_type_id_ci,
                )
            except ValueError:
                raise
            except Exception:
                logger.exception("Failed to re-deduct inventory at check-in for %s", booking_id)
                raise ValueError(
                    "No se pudo revalidar el inventario al registrar el check-in; inténtalo de nuevo."
                ) from None
            db.booking_orders.update_one(
                {"booking_id": booking_id},
                {
                    "$set": {
                        "inventory_re_deducted_at": utc_now(),
                        "inventory_re_deducted_by": changed_by,
                    }
                },
            )

    # ── Validate room status before check-in ──
    assigned_rooms: list[str] = booking.get("assigned_rooms") or []
    _room_docs: list[dict[str, Any]] = []

    if assigned_rooms:
        _room_docs = list(
            db.hotel_rooms.find(
                {"hotel_room_id": {"$in": assigned_rooms}},
                {"_id": 0, "hotel_room_id": 1, "room_label": 1},
            )
        )
        room_labels = {r["hotel_room_id"]: r.get("room_label", "") for r in _room_docs}
        status_query_labels = [v for v in room_labels.values() if v]
        if status_query_labels:
            status_docs = list(
                db.room_status_log.find(
                    {"prop_id": booking["prop_id"], "room_label": {"$in": status_query_labels}},
                    {"_id": 0, "room_label": 1, "status": 1},
                )
            )
            room_status_map: dict[str, str] = {r["room_label"]: r["status"] for r in status_docs}
            blocked: list[str] = []
            for h_id in assigned_rooms:
                label = room_labels.get(h_id, "")
                if not label:
                    continue
                status = room_status_map.get(label, "unknown")
                if status not in CHECKIN_ALLOWED_ROOM_STATUSES:
                    blocked.append(f"{label} ({status})")
            if blocked:
                raise ValueError(
                    f"No se puede realizar el check-in. Las siguientes habitaciones no están disponibles: "
                    f"{', '.join(blocked)}. Solo se permite check-in en habitaciones en estado 'vacante_limpia' o 'vacante_sucia'. "
                    f"Estados rechazados: {', '.join(sorted(CHECKIN_REJECTED_ROOM_STATUSES))}. "
                    "Liberá la habitación, limpiála o asigná otra disponible."
                )

    if early_mode and (not assigned_rooms or len(_room_docs) < len(assigned_rooms)):
        raise ValueError(
            "No se puede autorizar el early check-in: la reserva debe tener "
            "una habitación asignada y disponible. "
            "Asigná una habitación vacante antes de autorizar el early."
        )

    changed_at = utc_now()
    folio = _generate_folio(int(booking.get("prop_id", 0)))

    check_in_mode = early_mode or ("late_arrival" if is_late_arrival else "normal")
    check_in_set: dict[str, Any] = {
        "stay_status": "checked_in",
        "updated_at": changed_at,
        "folio": folio,
        "check_in_date_actual": actual_arrival_at.strftime("%Y-%m-%d"),
        "check_in_time_actual": actual_arrival_at.strftime("%H:%M"),
        "check_in_mode": check_in_mode,
        "check_in_by": changed_by,
        "payment_method": payment_method or booking.get("payment_method", ""),
    }
    if early_mode:
        check_in_set.update({
            "early_check_in_minutes": early_context["minutes_before"],
            "early_check_in_fee": early_fee,
            "early_check_in_approved": True,
            "early_check_in_approved_by": changed_by,
            "early_check_in_approved_at": changed_at,
            "early_check_in_reason": early_reason,
            "early_check_in_policy_time": early_context["check_in_time"],
        })
    if shift_id:
        # Front-desk check-ins are tied to the open cash shift at write time.
        # Service-level/test callers that pass no shift_id leave any shift
        # already stamped at booking creation untouched.
        check_in_set["shift_id"] = ObjectId(shift_id)

    result = db.booking_orders.find_one_and_update(
        {"booking_id": booking_id, "status": {"$nin": ["cancelled", "rejected"]}, "stay_status": {"$ne": "checked_in"}},
        {"$set": check_in_set},
        projection={"_id": 0, "is_test": 1},
    )
    if result is None:
        existing = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "status": 1, "stay_status": 1})
        if existing is None:
            raise ValueError("Reserva no encontrada. Verificá el identificador de la reserva.")
        if existing.get("stay_status") == "checked_in":
            raise ValueError(
                "La reserva ya está registrada como check-in. "
                "Usá el detalle de check-out para gestionar la salida."
            )
        raise ValueError(
            "No se puede hacer check-in con el estado actual de la reserva. "
            "Revisá el estado (pendiente, no-show o cancelada) y ajustá fechas "
            "o creá una reserva nueva."
        )

    audit_entry: dict[str, Any] = {
        "booking_id": booking_id, "status": "checked_in",
        "changed_at": changed_at, "reason": "front_desk_check_in",
        "changed_by": changed_by, "is_test": bool(result.get("is_test")),
        "check_in_method": "manual",
    }
    if ip_address:
        audit_entry["ip_address"] = ip_address
    if observations:
        audit_entry["observations"] = observations
    db.booking_status_history.insert_one(audit_entry)

    # ── Audit log (universal) ──
    if booking and not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="check_in",
                summary=f"Check-in completado — {booking.get('guest_name', '')} — Folio {folio}",
                changed_by=changed_by,
                metadata={"folio": folio, "guest_name": booking.get("guest_name", ""),
                         "payment_method": payment_method or booking.get("payment_method", ""),
                         "observations": observations, "check_in_mode": early_mode or "normal",
                         "early_check_in_fee": early_fee},
            )
        except Exception:
            logger.exception("Failed to register audit action for check-in %s", booking_id)

    # ── Notifications ──
    if booking:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            threading.Thread(target=_notify_guest_check_in, args=(booking_id, booking), daemon=True).start()
    if booking and not booking.get("is_test"):
        threading.Thread(target=_notify_staff_check_in, args=(booking_id, booking), daemon=True).start()
        if early_mode in ("early_approved", "early_courtesy"):
            # El equipo (recepción/housekeeping) debe saber que la llegada fue
            # anticipada y a qué hora real ocurrió (patrón notification_log)
            # — la habitación se ocupó antes de la hora de política y la
            # limpieza debe ajustarse. Aplica también a la cortesía (sin
            # cargo): la llegada anticipada afecta igual a la limpieza aunque
            # no haya fee.
            _notify_staff_window_extension(
                booking_id,
                booking,
                window="early_checkin",
                minutes=int(early_context.get("minutes_before", 0) or 0),
                policy_time=str(early_context.get("check_in_time") or ""),
                actual_time=actual_arrival_at.strftime("%H:%M"),
                fee=early_fee,
                reason=early_reason,
                mode=early_mode,
            )

    # ── Auto-create or retrieve invoice ──
    invoice_id: str | None = None
    if result and not result.get("is_test"):
        existing_inv = db.reservation_invoices.find_one({"booking_id": booking_id})
        # Decisión documentada: la rama de recuperación vincula CUALQUIER factura
        # existente (incluida una legacy en $0) en vez de crear una nueva — crear
        # una segunda factura junto a la $0 produciría un documento fiscal
        # duplicado. El invariante anti-$0 rige la CREACIÓN (guarda de
        # create_invoice + post-check abajo); las facturas legacy en $0 son un
        # problema de datos corregible por el backfill de facturas / auditoría
        # (``invoice_zero``), no por el check-in.
        if existing_inv:
            invoice_id = str(existing_inv["_id"])
        else:
            total = booking.get("total_price") if booking else None
            if total is not None and float(total) > 0:
                try:
                    from src.app.modules.billing.schemas import InvoiceCreate
                    from src.app.modules.billing.service import create_invoice
                    subtotal = float(total)
                    taxes = round(subtotal * 0.10, 2)
                    inv = create_invoice(InvoiceCreate(
                        booking_id=booking_id, subtotal=subtotal, taxes=taxes,
                        notes=f"Auto-generated invoice for booking {booking_id} at check-in",
                    ))
                    # Guard extendido: el check-in nunca vincula una factura en
                    # $0/negativa, aunque create_invoice llegara a devolver una
                    # (defensa en profundidad del invariante anti-$0).
                    if inv and (inv.get("total") or 0) > 0:
                        invoice_id = inv.get("id")
                except Exception:
                    logger.exception("Failed to auto-create invoice at check-in for booking %s", booking_id)

    # ── Mark rooms as occupied ──
    if assigned_rooms and booking:
        try:
            for r in _room_docs:
                label = r.get("room_label", "")
                if label:
                    from src.app.modules.housekeeping.schemas import RoomStatusLogCreate
                    from src.app.modules.housekeeping.service.lifecycle.status import (
                        upsert_room_status,
                    )
                    upsert_room_status(RoomStatusLogCreate(
                        prop_id=booking["prop_id"],
                        room_type_id=r.get("room_type_id", ""),
                        room_label=label,
                        status="occupied_clean",
                        note=f"Check-in: {booking_id}",
                    ))
            logger.info("Rooms marked as occupied for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to mark rooms as occupied for booking %s", booking_id)

    # ── Notify housekeeping ──
    if assigned_rooms and booking and not booking.get("is_test"):
        try:
            room_labels_str = ", ".join(
                r.get("room_label", "") for r in _room_docs
            ) or str(len(assigned_rooms))
            db.notification_log.insert_one({
                "notification_type": "housekeeping_check_in",
                "entity_type": "booking", "entity_id": booking_id,
                "prop_id": booking["prop_id"], "recipient_email": "",
                "subject": f"Check-in: habitación(es) {room_labels_str} ocupadas",
                "message": (
                    f"El huésped {booking.get('guest_name', '')} ha realizado el check-in. "
                    f"Habitación(es): {room_labels_str}. "
                    f"Check-out: {booking.get('check_out_date', '')}."
                ),
                "status": "pending", "created_at": changed_at,
                "metadata": {"booking_id": booking_id, "assigned_rooms": assigned_rooms,
                             "guest_name": booking.get("guest_name", ""),
                             "check_out_date": booking.get("check_out_date", "")},
            })
        except Exception:
            logger.exception("Failed to notify housekeeping for booking %s", booking_id)

    # ── Create folio ──
    folio_id: str | None = None
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.billing.service import create_folio, post_to_folio
            folio_doc = create_folio(booking_id, shift_id=shift_id)
            if folio_doc:
                folio_id = folio_doc.get("folio_number")
                if early_fee > 0:
                    posted = post_to_folio(
                        booking_id,
                        category_id="early_checkin",
                        concept=f"Early check-in autorizado — {early_context['minutes_before']} min antes",
                        amount=early_fee,
                        reference_id=f"{booking_id}:early_check_in",
                        reference_type="early_check_in",
                        shift_id=shift_id,
                    )
                    if posted is None:
                        logger.error("Could not post early check-in fee for booking %s", booking_id)
                logger.info("Folio %s created for booking %s at check-in", folio_id, booking_id)
        except Exception:
            logger.exception("Failed to create folio for booking %s", booking_id)

    # ── Register shift transaction ──
    # Re-read the folio AFTER the early fee was posted (and the folio itself
    # created): the booking fetch at the top of the flow predates the folio,
    # so a bare ``txn_type="check_in"`` would register amount=0 and the shift
    # report would under-collect the early check-in. Use the fresh total_due
    # (room + charges − discounts − payments) so the shift reconciles against
    # the folio, mirroring the check-out hardening.
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            fresh_folio = db.guest_folios.find_one({"booking_id": booking_id})
            total_due = round(float(fresh_folio.get("total_due", 0) or 0), 2) if fresh_folio else float(booking.get("total_price", 0) or 0)
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="check_in", booking_id=booking_id,
                amount=total_due, payment_method=payment_method or "",
                description=f"Check-in: {booking.get('guest_name', '')} — Folio {folio} — ${total_due:.2f}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for check-in %s", booking_id)

    return {"booking_id": booking_id, "stay_status": "checked_in", "folio": folio,
            "folio_number": folio_id, "invoice_id": invoice_id,
            "check_in_mode": check_in_mode, "early_check_in_mode": early_mode,
            "early_check_in_fee": early_fee}
