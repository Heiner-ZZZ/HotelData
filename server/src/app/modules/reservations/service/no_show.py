"""No-show processing — integrated into the reservations service module.

A no-show occurs when a guest with a confirmed reservation never arrives
on check-in day. The hotel charges the first night as penalty.

- process_no_show(): marks a single booking as no-show, charges penalty,
  restores inventory, posts to folio, sends notification email.
- auto_process_no_shows(): scheduled daily task that finds confirmed
  bookings whose check-in date has passed without arrival.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from src.app.core.state_machine import stay_sm
from src.app.core.timezone import local_today
from src.app.modules.partner.services.audit import register_action
from src.app.modules.reservations.service.late_arrival import (
    late_arrival_cutoff_reached,
    protected_from_auto_no_show,
    resolve_late_arrival_policies,
)
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def ensure_no_show_folio(
    db: Any,
    booking: dict[str, Any],
    *,
    penalty_amount: float | None = None,
    penalty_pct: int | None = None,
    check_in_str: str | None = None,
    now: datetime | None = None,
) -> str | None:
    """Create or recover the penalty folio for a persisted no-show.

    Older no-show records used only the first eight booking-id characters in
    ``folio_number``. That value collides for bookings from the same date and
    can leave ``stay_status=no_show`` saved without a folio. This helper uses
    the full booking id, retries on a concurrent unique-number race, and is
    idempotent for both the write path and the recovery read path.
    """
    booking_id = str(booking.get("booking_id") or "")
    if not booking_id:
        return None

    collection = db["guest_folios"]
    existing = collection.find_one({"booking_id": booking_id}, {"folio_number": 1})
    if existing:
        return existing.get("folio_number")

    amount = round(float(
        penalty_amount if penalty_amount is not None else booking.get("no_show_penalty_amount", 0) or 0
    ), 2)
    percent = int(penalty_pct if penalty_pct is not None else booking.get("no_show_penalty_percent", 0) or 0)
    check_in = str(check_in_str or booking.get("check_in_date", ""))[:10]
    timestamp = now or _now()
    base_number = f"FL-NS-{booking_id.upper()}"

    # The booking id is unique, but the suffix also makes recovery safe if a
    # legacy record already owns the full candidate or another request races us.
    for suffix in range(100):
        folio_number = base_number if suffix == 0 else f"{base_number}-{suffix + 1}"
        if collection.find_one({"folio_number": folio_number}, {"_id": 1}):
            continue
        try:
            collection.insert_one({
                "folio_number": folio_number,
                "booking_id": booking_id,
                "prop_id": int(booking.get("prop_id", 0) or 0),
                "guest_name": booking.get("guest_name", ""),
                "guest_email": booking.get("guest_email", ""),
                "room_label": "",
                "hotel_label": "",
                "currency": booking.get("currency", "USD"),
                "check_in_date": check_in,
                "check_out_date": str(booking.get("check_out_date", "")),
                "status": "open",
                "total_room": 0.0,
                "total_charges": amount,
                "total_discounts": 0.0,
                "total_payments": 0.0,
                "total_due": amount,
                "postings": [{
                    "posting_id": ObjectId(),
                    "type": "charge",
                    "category": "Penalización",
                    "concept": f"No-show — Penalización del {percent}% de 1 noche ({check_in})",
                    "amount": amount,
                    "quantity": 1,
                    "unit_price": amount,
                    "reference_id": booking_id,
                    "reference_type": "no_show_penalty",
                    "posted_at": timestamp,
                }],
                "posting_count": 1,
                "created_at": timestamp,
                "closed_at": None,
                "closed_by": None,
                "invoice_id": None,
            })
            return folio_number
        except DuplicateKeyError:
            existing = collection.find_one({"booking_id": booking_id}, {"folio_number": 1})
            if existing:
                return existing.get("folio_number")

    raise RuntimeError(f"No fue posible generar un número de folio para {booking_id}")


def process_no_show(
    booking_id: str,
    *,
    changed_by: str = "no_show_scheduler",
) -> dict[str, Any]:
    """Mark a confirmed booking as no-show and charge first night penalty.

    Only applicable to bookings with status="confirmed" and stay_status="pending"
    whose check-in date has already passed.

    Returns {"ok": True, "penalty_amount": X.XX} or raises ValueError.
    """
    db = get_database()

    # stay_status puede estar ausente/vacío en reservas confirmadas legacy que
    # nunca llegaron a check-in — son tan no-show como las ``pending`` explícitas.
    booking = db.booking_orders.find_one(
        {
            "booking_id": booking_id,
            "status": "confirmed",
            "$or": [
                {"stay_status": "pending"},
                {"stay_status": {"$exists": False}},
                {"stay_status": ""},
                {"stay_status": None},
            ],
        },
    )
    if not booking:
        raise ValueError(
            "Reserva no encontrada o no está en estado válido para no-show. "
            "Verificá el estado: solo se marcan reservas confirmadas pendientes de check-in."
        )

    check_in_str = str(booking.get("check_in_date", ""))[:10]
    try:
        check_in_date = date.fromisoformat(check_in_str)
    except ValueError:
        raise ValueError(f"Fecha de check-in inválida: {check_in_str}")

    today = date.fromisoformat(local_today())
    if check_in_date > today:
        raise ValueError(
            f"No se puede marcar como no-show antes del check-in "
            f"({check_in_str}). Hoy es {today}. "
            "Esperá al día del check-in (o después) para marcarlo, "
            "o ajustá la fecha de llegada de la reserva."
        )

    # Calculate first night penalty — read penalty % from hotel_policies
    from src.app.modules.reservations.service import (
        resolve_penalty_percent,
        room_rate_per_night,
    )
    penalty_pct = resolve_penalty_percent(
        prop_id=int(booking.get("prop_id", 0)),
        room_type_id=str(booking.get("room_type_id", "")),
        rate_plan_id=str(booking.get("rate_plan_id", "")),
    )
    rate_per_night = room_rate_per_night(booking)
    penalty_amount = round(rate_per_night * penalty_pct / 100, 2)

    # If penalty_pct > 0 but rate is so low it rounds to zero, charge at least the full night
    if penalty_pct > 0 and penalty_amount <= 0:
        penalty_amount = rate_per_night

    now = _now()

    # Update booking
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$set": {
                "stay_status": "no_show",
                "no_show_penalty_amount": penalty_amount,
                "no_show_penalty_percent": penalty_pct,
                "no_show_processed_at": now,
                "no_show_processed_by": changed_by,
                "updated_at": now,
            }
        },
    )

    # Restore inventory (rooms were deducted on confirm, release them)
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
        logger.exception("Failed to restore inventory for no-show %s", booking_id)

    # Create minimal folio with penalty only (no room charge — guest never checked in)
    folio_number: str | None = None
    try:
        from src.app.modules.billing.service.folio import FOLIO_COLLECTION

        existing_folio = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
        if not existing_folio:
            folio_number = ensure_no_show_folio(
                db,
                booking,
                penalty_amount=penalty_amount,
                penalty_pct=penalty_pct,
                check_in_str=check_in_str,
                now=now,
            )
        else:
            folio_number = existing_folio.get("folio_number")
            from src.app.modules.billing.service.folio import post_to_folio
            post_to_folio(
                booking_id,
                posting_type="charge",
                category_id="no_show",
                concept=f"No-show — Penalización del {penalty_pct}% de 1 noche ({check_in_str})",
                amount=penalty_amount,
                quantity=1,
                reference_id=booking_id,
                reference_type="no_show_penalty",
            )
    except Exception:
        logger.exception("Failed to post no-show penalty to folio for %s", booking_id)
        folio_number = None

    # La estadía NO ocurrió: anular la factura de estadía emitida al confirmar
    # (si no tiene pagos). El cobrable pasa al folio de penalización; la
    # factura no debe seguir mostrándose como "pendiente de pago".
    try:
        from src.app.modules.billing.service.lifecycle.invoices import cancel_stay_invoice_for_no_stay
        cancel_stay_invoice_for_no_stay(
            booking_id,
            reason=(
                f"No-show — penalización ${penalty_amount:.2f} "
                f"({penalty_pct}% de 1 noche); folio {folio_number or 'N/A'} — "
                "la estadía no se factura."
            ),
            cancelled_by=changed_by,
        )
    except Exception:
        logger.exception("Failed to cancel stay invoice for no-show %s", booking_id)

    # Log in history
    reason_detail = (
        f"No-show — penalización: ${penalty_amount:.2f} "
        f"({penalty_pct}% de 1 noche de {booking.get('total_nights', 1)} reservadas)"
    )
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": "no_show",
        "changed_at": now,
        "reason": reason_detail,
        "changed_by": changed_by,
        "is_test": bool(booking.get("is_test")),
    })

    # Audit log
    if not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="no_show",
                summary=f"No-show registrado — {booking.get('guest_name', '')} — penalización ${penalty_amount:.2f}",
                changed_by=changed_by,
                metadata={
                    "guest_name": booking.get("guest_name", ""),
                    "check_in_date": check_in_str,
                    "penalty_amount": penalty_amount,
                },
            )
        except Exception:
            logger.exception("Failed to register audit action for no-show %s", booking_id)

    # Deactivate stay session if exists
    try:
        db.stay_sessions.update_many(
            {"booking_id": booking_id, "active": True},
            {"$set": {"active": False, "deactivated_at": now}},
        )
    except Exception:
        logger.exception("Failed to deactivate stay session for no-show %s", booking_id)

    # Notify guest via email
    try:
        guest_email = (booking.get("guest_email") or "").strip()
        if guest_email and not booking.get("is_test"):
            from src.app.modules.reservations.notifications import (
                notify_guest_status_change,
            )
            notify_guest_status_change(
                booking_id=booking_id,
                guest_name=booking.get("guest_name", ""),
                guest_email=guest_email,
                new_status="no_show",
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=check_in_str,
                check_out_date=str(booking.get("check_out_date", "")),
                total_price=booking.get("total_price"),
                currency=booking.get("currency", "USD"),
                total_nights=int(booking.get("total_nights", 0)),
                reason=reason_detail,
            )
    except Exception:
        logger.exception("Failed to notify guest on no-show for booking %s", booking_id)

    logger.info(
        "No-show processed for booking %s: $%.2f penalty charged",
        booking_id, penalty_amount,
    )

    return {
        "ok": True,
        "booking_id": booking_id,
        "penalty_amount": penalty_amount,
        "check_in_date": check_in_str,
        "folio_number": folio_number,
    }


def auto_process_no_shows() -> dict[str, Any]:
    """Daily task: find confirmed bookings whose check-in date has passed.

    Processes bookings with status="confirmed", stay_status="pending" (o
    campo ausente/vacío) que no llegaron. Respeta la política configurable por
    hotel (``scripts`` → ``service/late_arrival.py``):

    - ``no_show_execution=manual``  → el hotel nunca se procesa automáticamente.
    - ``guaranteed_reservation``    → la reserva garantizada nunca se procesa sola.
    - llegada tardía declarada       → ``late_checkin`` / ``estimated_arrival_time``
      / ``declared_late_arrival`` protegen la reserva.
    - ``no_show_execution=same_day_cutoff`` → la reserva de HOY entra como
      candidata una vez pasada la hora límite de llegada.

    Returns a summary dict with counts of processed/skipped no-shows and errors.
    """
    db = get_database()
    today_str = local_today()
    today = date.fromisoformat(today_str)

    candidates = list(
        db.booking_orders.find(
            {
                "status": "confirmed",
                "$or": [
                    {"stay_status": "pending"},
                    {"stay_status": {"$exists": False}},
                    {"stay_status": ""},
                    {"stay_status": None},
                ],
                "check_in_date": {"$lte": today_str},
            },
            {
                "_id": 0,
                "booking_id": 1,
                "guest_name": 1,
                "guest_email": 1,
                "is_test": 1,
                "prop_id": 1,
                "check_in_date": 1,
                "check_out_date": 1,
                "total_price": 1,
                "currency": 1,
                "total_nights": 1,
                "late_checkin": 1,
                "estimated_arrival_time": 1,
                "declared_late_arrival": 1,
            },
        )
    )

    if not candidates:
        logger.info("auto_process_no_shows: no bookings to process")
        return {"processed": 0, "errors": [], "candidate_count": 0, "skipped": {}}

    prop_ids = sorted({int(b.get("prop_id", 0) or 0) for b in candidates})
    policies = resolve_late_arrival_policies(db, prop_ids)

    processed = 0
    errors: list[str] = []
    skipped: dict[str, int] = {"manual": 0, "guaranteed": 0, "declared_late_arrival": 0, "same_day_not_yet": 0}

    for booking in candidates:
        booking_id = booking["booking_id"]
        policy = policies.get(int(booking.get("prop_id", 0) or 0), {})

        if policy.get("no_show_execution") == "manual":
            skipped["manual"] += 1
            continue
        if protected_from_auto_no_show(booking, policy):
            if policy.get("guaranteed_reservation"):
                skipped["guaranteed"] += 1
            else:
                skipped["declared_late_arrival"] += 1
            continue

        check_in_str = str(booking.get("check_in_date") or "")[:10]
        try:
            check_in_date = date.fromisoformat(check_in_str)
        except ValueError:
            logger.warning("auto_no_show: fecha ilegible %r para %s", check_in_str, booking_id)
            continue
        if check_in_date > today:
            continue
        if check_in_date == today and policy.get("no_show_execution") != "same_day_cutoff":
            # next_day: la reserva de hoy todavía no es candidata.
            skipped["same_day_not_yet"] += 1
            continue
        if check_in_date == today and not late_arrival_cutoff_reached(policy):
            # same_day_cutoff pero aún no pasó la hora límite de llegada.
            skipped["same_day_not_yet"] += 1
            continue

        try:
            process_no_show(booking_id, changed_by="no_show_scheduler")
            processed += 1
            logger.info("Auto no-show processed for booking %s", booking_id)
        except Exception as exc:
            err_msg = f"{booking_id}: {exc}"
            errors.append(err_msg)
            logger.exception("Failed to process no-show for booking %s", booking_id)

    # Log execution
    try:
        db.etl_executions.insert_one({
            "execution_id": f"NO_SHOW_{_now().strftime('%Y%m%d%H%M%S')}",
            "executed_at": _now(),
            "pipeline": "auto_no_show",
            "status": "completed" if not errors else "completed_with_errors",
            "summary": {
                "candidates_found": len(candidates),
                "processed": processed,
                "skipped": skipped,
                "errors": len(errors),
            },
        })
    except Exception:
        logger.exception("Failed to log auto_no_show execution")

    return {
        "processed": processed,
        "errors": errors,
        "candidate_count": len(candidates),
        "skipped": skipped,
    }


def reopen_window_reason(
    booking: dict[str, Any],
    today_str: str | None = None,
) -> str | None:
    """Ventana de reapertura de un no-show — misma regla que ``reopen_no_show``.

    Devuelve ``None`` cuando la reserva es reabrible (check-in de HOY o AYER
    y estadía vigente, check-out sin vencer), o el motivo de bloqueo:
    ``'too_late'`` (check-in con 2+ días de retraso) o ``'stay_ended'``
    (check-out ya pasó). Fechas faltantes/ilegibles se ignoran (lenient, como
    el guard). Los valores espejan ``reopenWindowBlockedReason`` de la UI
    (check-in-detail-page) para que el calendario de Recepción y el detalle
    marquen la MISMA ventana sin duplicar la regla.
    """
    today_date = date.fromisoformat(today_str or local_today())
    try:
        ci_date = date.fromisoformat(str(booking.get("check_in_date", "") or ""))
    except (ValueError, TypeError):
        ci_date = None
    try:
        co_date = date.fromisoformat(str(booking.get("check_out_date", "") or ""))
    except (ValueError, TypeError):
        co_date = None
    if ci_date is not None and ci_date < today_date and (today_date - ci_date).days > 1:
        return "too_late"
    if co_date is not None and co_date < today_date:
        return "stay_ended"
    return None


def _remove_no_show_penalty_folio(
    db: Any,
    booking_id: str,
    *,
    now: datetime,
) -> dict[str, Any]:
    """Retirar el folio de penalización del no-show al reabrir la reserva.

    El folio de penalización es un artefacto dedicado que solo contiene el
    cargo ``no_show_penalty``. Cuando el gerente reabre la reserva el huésped
    llegó, así que la penalización no debe sobrevivir:

    - Folio con SOLO el cargo de penalización (sin pagos ni otros cargos) →
      se elimina por completo.
    - Folio con pagos u otros cargos → la penalización se revierte con un
      ``charge_reversal`` (evento compensatorio inmutable); el folio y su
      historial de pagos se conservan para que el gerente los gestione en
      Facturación.
    - Sin folio → no hay nada que retirar (read path de recuperación).

    Returns:
        {"removed": bool, "reversed": bool, "folio_number": str | None,
         "reversal_amount": float}
    """
    from src.app.modules.billing.service.folio import FOLIO_COLLECTION, post_to_folio

    folio = db[FOLIO_COLLECTION].find_one({"booking_id": booking_id})
    if not folio:
        return {"removed": False, "reversed": False, "folio_number": None, "reversal_amount": 0.0}

    folio_number = folio.get("folio_number")
    postings = folio.get("postings") or []
    penalty_postings = [
        p for p in postings if str(p.get("reference_type") or "") == "no_show_penalty"
    ]
    other_postings = [
        p for p in postings if str(p.get("reference_type") or "") != "no_show_penalty"
    ]

    if not penalty_postings:
        # No hay cargo de penalización en el folio → no hay nada que retirar.
        return {"removed": False, "reversed": False, "folio_number": folio_number, "reversal_amount": 0.0}

    penalty_total = round(sum(float(p.get("amount", 0) or 0) for p in penalty_postings), 2)

    if not other_postings:
        # Folio de penalización puro: se elimina — es un artefacto fantasma
        # de un huésped que nunca se hospedó.
        db[FOLIO_COLLECTION].delete_one({"_id": folio["_id"]})
        return {"removed": True, "reversed": False, "folio_number": folio_number, "reversal_amount": penalty_total}

    # El folio arrastra pagos/otros cargos: se revierte solo la penalización
    # con un evento compensatorio inmutable (historial intacto, saldo a cero).
    try:
        post_to_folio(
            booking_id,
            posting_type="charge_reversal",
            category_id="no_show",
            concept="No-show revertido por reapertura de reserva",
            amount=penalty_total,
            quantity=1,
            reference_id=f"{booking_id}:no_show_reopen:{now.strftime('%Y%m%d%H%M%S%f')}",
            reference_type="no_show_penalty_reversal",
        )
        return {"removed": False, "reversed": True, "folio_number": folio_number, "reversal_amount": penalty_total}
    except Exception:
        logger.exception("Failed to reverse no-show penalty on reopen for %s", booking_id)
        return {"removed": False, "reversed": False, "folio_number": folio_number, "reversal_amount": penalty_total}


def _notify_staff_no_show_reopen(
    booking_id: str,
    booking: dict[str, Any],
    *,
    reason: str,
    changed_by: str,
    penalty_removed: bool,
) -> None:
    """Fire-and-forget: broadcast a la campanita (``notification_log`` con
    ``recipient_email`` vacío) para que recepción/housekeeping sepan que el
    huésped del no-show llegará tarde y la reserva volvió a ``pending``.

    Mismo patrón de broadcast operativo del check-in (``housekeeping_check_in``)
    y de las extensiones de ventana early/late (``_notify_staff_window_extension``):
    entrada sin destinatario que la campanita
    muestra a todo el staff del hotel.
    """
    try:
        db = get_database()
        guest_name = str(booking.get("guest_name", "") or "").strip() or "el huésped"
        penalty_line = (
            " La penalización de no-show fue retirada." if penalty_removed else ""
        )
        db.notification_log.insert_one({
            "notification_type": "no_show_reopen",
            "entity_type": "booking",
            "entity_id": booking_id,
            "prop_id": int(booking.get("prop_id", 0) or 0),
            "recipient_email": "",
            "subject": f"No-show reabierto — {guest_name} llegará tarde ({booking_id})",
            "message": (
                f"El gerente reabrió el no-show de {guest_name}: la reserva volvió a "
                "pendiente y el huésped llegará tarde "
                f"(check-in {booking.get('check_in_date', '')}, "
                f"check-out {booking.get('check_out_date', '')}). "
                f"Motivo: {reason}.{penalty_line}"
            ),
            "status": "pending",
            "created_at": _now(),
            "metadata": {
                "booking_id": booking_id,
                "guest_name": guest_name,
                "check_in_date": booking.get("check_in_date", ""),
                "check_out_date": booking.get("check_out_date", ""),
                "reopen_reason": reason,
                "reopened_by": changed_by,
                "no_show_penalty_removed": penalty_removed,
            },
        })
        logger.info("No-show reopen broadcast queued for booking %s", booking_id)
    except Exception:
        logger.exception("Failed to notify staff about no-show reopen for booking %s", booking_id)


def reopen_no_show(
    booking_id: str,
    *,
    reason: str,
    changed_by: str = "web",
) -> dict[str, Any]:
    """Reabrir una reserva cerrada como no-show (autorización de gerente).

    El huésped llegó después de que el no-show fue procesado (política de
    llegadas: "reapertura o autorización de gerente; no check-in normal"). La
    reserva vuelve a ``stay_status=pending`` para que el flujo de check-in
    (incluida la ventana de llegada tardía) funcione de nuevo.

    El folio de la penalización se RETIRA: si solo contiene la penalización se
    elimina por completo; si arrastra pagos u otros cargos la penalización se
    revierte con un ``charge_reversal`` y el folio se conserva para que el
    gerente lo gestione en Facturación. Queda traza en la reserva
    (``no_show_reopened_at/by/reason`` + ``no_show_penalty_removed*``), en
    ``booking_status_history`` y en el audit log (lo registra la ruta).

    Raises ValueError si la reserva no existe, no está en no-show o falta el
    motivo.
    """
    db = get_database()

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "_id": 0,
            "status": 1,
            "stay_status": 1,
            "no_show_penalty_amount": 1,
            "prop_id": 1,
            "check_in_date": 1,
            "check_out_date": 1,
            "rooms": 1,
            "room_type_id": 1,
            "is_test": 1,
            "guest_name": 1,
        },
    )
    if not booking:
        raise ValueError("Reserva no encontrada.")
    # Guard centralizado en el state machine de Stay: la ÚNICA salida de
    # ``no_show`` es la reapertura gerencial (``no_show → pending``). El mensaje
    # de negocio se conserva; la regla vive en ``src/app/core/state_machine.py``.
    current_stay = str(booking.get("stay_status") or "").strip().lower()
    if not stay_sm.can_transition(current_stay, "pending"):
        raise ValueError(
            "La reserva no está marcada como no-show; no se puede reabrir. "
            "La reapertura aplica solo a reservas en no-show — si sigue pendiente, "
            "hacé el check-in normal."
        )

    clean_reason = str(reason or "").strip()
    if not clean_reason:
        raise ValueError("El motivo de la reapertura es obligatorio.")

    # ── Ventana de reapertura: hoy o ayer con estadía vigente ──
    # Reabrir un no-show muy antiguo colapsaría la estancia con las de otras
    # fechas (inventario, folios, facturación). La ventana es la misma de la
    # llegada tardía: check-in de HOY (0) o AYER (1) y check-out sin vencer.
    # Fuera de la ventana el mensaje apunta a ajustar fechas / nueva reserva.
    window_reason = reopen_window_reason(booking)
    if window_reason == "too_late":
        today_date = date.fromisoformat(local_today())
        ci_date = date.fromisoformat(str(booking.get("check_in_date", "") or ""))
        days_late = (today_date - ci_date).days
        raise ValueError(
            f"No se puede reabrir: la reserva tiene {days_late} día(s) de retraso "
            "y la ventana de reapertura cerró. Ajustá las fechas o creá una reserva nueva."
        )
    if window_reason == "stay_ended":
        raise ValueError(
            f"No se puede reabrir: la estadía ya terminó ({booking.get('check_out_date')}). "
            "Solo se reabren no-shows con estadía vigente (check-in de hoy o ayer). "
            "Ajustá las fechas o creá una reserva nueva."
        )

    now = _now()

    # ── Re-validar y re-deducir el inventario de las noches de la estancia ──
    # El no-show liberó las noches (``_restore_inventory``); reabrir debe
    # volver a tomarlas ANTES de mutar la reserva. ``_deduct_inventory`` valida
    # TODA la estancia en una transacción: si una noche ya fue re-vendida o
    # falta el dato, la reapertura FALLA aquí sin escribir nada — el huésped
    # no puede re-alojarse en noches sin disponibilidad. Las reservas sin
    # ``room_type_id`` no tienen inventario nocturno que gestionar (misma
    # semántica del restore): se reabren sin re-deducción.
    room_type_id_reopen = str(booking.get("room_type_id", "") or "")
    inventory_re_deducted_at: Any | None = None
    if room_type_id_reopen:
        try:
            from src.app.modules.reservations.service._transitions import (
                _deduct_inventory,
            )
            _deduct_inventory(
                prop_id=int(booking.get("prop_id", 0) or 0),
                check_in_date=str(booking.get("check_in_date", "") or ""),
                check_out_date=str(booking.get("check_out_date", "") or ""),
                rooms=int(booking.get("rooms", 1) or 1),
                room_type_id=room_type_id_reopen,
            )
        except ValueError:
            raise
        except Exception:
            logger.exception("Failed to re-deduct inventory on reopen for %s", booking_id)
            raise ValueError(
                "No se pudo revalidar el inventario al reabrir la reserva; inténtalo de nuevo."
            ) from None
        inventory_re_deducted_at = now

    reopen_set: dict[str, Any] = {
        "stay_status": "pending",
        "no_show_reopened_at": now,
        "no_show_reopened_by": changed_by,
        "no_show_reopen_reason": clean_reason,
        "updated_at": now,
    }
    if inventory_re_deducted_at is not None:
        # Marca de idempotencia: el check-in de una reserva reabierta NO vuelve
        # a deducir (la red de seguridad de ``complete_check_in`` la respeta).
        reopen_set["inventory_re_deducted_at"] = inventory_re_deducted_at
        reopen_set["inventory_re_deducted_by"] = changed_by

    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": reopen_set},
    )

    # Retirar el folio de penalización: el huésped llegó, la penalización no
    # debe sobrevivir. Folio penalty-only → se elimina; con pagos/cargos → el
    # cargo se revierte (evento compensatorio inmutable).
    folio_outcome = _remove_no_show_penalty_folio(db, booking_id, now=now)
    if folio_outcome["removed"] or folio_outcome["reversed"]:
        db.booking_orders.update_one(
            {"booking_id": booking_id},
            {
                "$set": {
                    "no_show_penalty_removed": True,
                    "no_show_penalty_removed_at": now,
                    "no_show_penalty_removed_by": changed_by,
                    "no_show_penalty_removed_reason": clean_reason,
                }
            },
        )

    folio_trace = (
        "folio eliminado"
        if folio_outcome["removed"]
        else ("cargo revertido en folio" if folio_outcome["reversed"] else "sin folio")
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "pending",
            "changed_at": now,
            "reason": f"no_show_reopen: {clean_reason} — penalización retirada ({folio_trace})",
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )

    # ── Broadcast a la campanita ──
    # Recepción/housekeeping deben saber que el huésped del no-show llegará
    # tarde y la reserva volvió a ``pending``. Fire-and-forget, mismo canal de
    # broadcasts operativos (``housekeeping_check_in``, late/early check-in/out).
    # Las reservas ``is_test`` no generan notificaciones (misma regla del check-in).
    if not booking.get("is_test"):
        _notify_staff_no_show_reopen(
            booking_id,
            booking,
            reason=clean_reason,
            changed_by=changed_by,
            penalty_removed=bool(folio_outcome["removed"] or folio_outcome["reversed"]),
        )

    return {
        "ok": True,
        "booking_id": booking_id,
        "stay_status": "pending",
        "penalty_amount": booking.get("no_show_penalty_amount") or 0,
        "folio_number": folio_outcome["folio_number"],
        "penalty_removed": folio_outcome["removed"] or folio_outcome["reversed"],
        "folio_deleted": folio_outcome["removed"],
        "reversal_amount": folio_outcome["reversal_amount"],
        "inventory_re_deducted": inventory_re_deducted_at is not None,
    }
