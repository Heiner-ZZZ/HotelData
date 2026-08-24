"""Check-out operations."""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId

from src.app.core.timezone import local_now, local_today
from src.app.modules.partner.services.audit import register_action
from src.app.modules.reservations.service._checkinout._helpers import (
    _notify_guest_check_out,
    _notify_staff_check_out,
    _notify_staff_window_extension,
)
from src.database.connection import get_database

from .._helpers import utc_now
from .._transitions import _restore_inventory
from ._checkin import _parse_time_minutes, _policy_bool

logger = logging.getLogger(__name__)


_LATE_CHECK_OUT_MODES = {"late_courtesy", "late_approved"}


def _invoice_is_immutable(db, booking_id: str) -> bool:
    """¿La factura del huésped es una snapshot fiscal inmutable?

    Espejo de la condición del módulo billing (``update_invoice_additional_charges``):
    pagada / parcialmente pagada / refunded / cancelled, o con pagos confirmados.
    Una factura inmutable no puede reescribirse — el plegado de cargos fallaría.
    """
    inv = db.reservation_invoices.find_one(
        {"booking_id": booking_id}, {"_id": 1, "status": 1}
    )
    if not inv:
        return False
    if inv.get("status") in {"paid", "partially_paid", "refunded", "cancelled"}:
        return True
    return (
        db.reservation_payments.count_documents(
            {"invoice_id": inv["_id"], "status": {"$in": ["confirmed", "refunded"]}}
        )
        > 0
    )


def _has_active_additional_charges(db, booking_id: str) -> bool:
    """¿Quedan cargos adicionales activos sin facturar? (los reversados no cuentan)."""
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION

    return (
        db[CHARGES_COLLECTION].count_documents(
            {"booking_id": booking_id, "status": {"$ne": "reversed"}}
        )
        > 0
    )


def get_late_checkout_context(
    prop_id: int,
    check_out_date: str,
    *,
    now: Any | None = None,
    db: Any | None = None,
) -> dict[str, Any]:
    """Resolve the server-authoritative late check-out state for a booking.

    Deliberately read-only, mirror of ``get_early_check_in_context``: it
    compares the hotel's configured check-out time with the current local time
    only when the stay ends today (``check_out_date == today``). A departure
    before the scheduled hour is normal; on the scheduled day after the hour it
    is late. Early departure (before ``check_out_date``) and overstay (after)
    are different scenarios, not late check-out, so the same-day guard keeps
    them out of this window. It never changes reservation dates or inventory.
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
            "check_out_time": 1,
            "late_checkout_enabled": 1,
            "late_checkout_courtesy_minutes": 1,
            "late_checkout_default_fee": 1,
        },
    ) or {}

    check_out_time = str(policy.get("check_out_time") or "").strip()
    schedule_minutes = _parse_time_minutes(check_out_time)
    try:
        courtesy_minutes = max(0, min(int(policy.get("late_checkout_courtesy_minutes", 60) or 60), 240))
    except (TypeError, ValueError):
        courtesy_minutes = 60
    try:
        default_fee = max(0.0, round(float(policy.get("late_checkout_default_fee", 0) or 0), 2))
    except (TypeError, ValueError):
        default_fee = 0.0

    enabled = _policy_bool(policy.get("late_checkout_enabled"), True)
    current = now or local_now()
    context: dict[str, Any] = {
        "enabled": enabled,
        "is_late": False,
        "minutes_after": 0,
        "courtesy_minutes": courtesy_minutes,
        "requires_approval": False,
        "check_out_time": check_out_time,
        "default_fee": default_fee,
        # Hora real de la salida (reloj local del servidor): campo legible para
        # recepción — cuándo está ocurriendo/ocurrió la salida extendida.
        "real_time": "",
    }
    # Sin política habilitada no existe ventana late: la salida es normal
    # (a diferencia del early check-in, la salida no se puede bloquear — el
    # huésped se va; la ventana solo gobierna cargo/aprobación).
    if (
        not enabled
        or schedule_minutes is None
        or not check_out_date
        or check_out_date != local_today()
    ):
        return context

    current_minutes = current.hour * 60 + current.minute
    minutes_after = current_minutes - schedule_minutes
    if minutes_after <= 0:
        return context

    context["is_late"] = True
    context["minutes_after"] = minutes_after
    context["requires_approval"] = minutes_after > courtesy_minutes
    context["real_time"] = current.strftime("%H:%M")
    return context


def validate_late_checkout(
    context: dict[str, Any],
    *,
    mode: str | None,
    approved: bool,
    reason: str,
    fee: Any,
) -> tuple[str | None, float, str]:
    """Validate an explicit late-departure decision before any state write."""
    normalized_mode = str(mode or "").strip().lower() or None
    normalized_reason = str(reason or "").strip()
    # Mensajes con acción (criterio compartido con el flujo de no-show): además
    # de describir el estado, dicen QUÉ hacer — derivar al gerente, marcar la
    # aprobación, escribir el motivo o corregir el cargo.
    if not context["enabled"] and normalized_mode in _LATE_CHECK_OUT_MODES:
        raise ValueError(
            "El late check-out está deshabilitado para este hotel. "
            "Procedé con el check-out normal en el horario de salida, o pedile al gerente "
            "que lo habilite en Políticas si necesita extenderse."
        )
    if not context["is_late"]:
        if normalized_mode in _LATE_CHECK_OUT_MODES:
            raise ValueError(
                "La reserva ya está dentro del horario normal de check-out. "
                "Procedé con el check-out normal sin cargo extra."
            )
        return None, 0.0, ""
    if normalized_mode not in _LATE_CHECK_OUT_MODES or not approved:
        raise ValueError(
            "El late check-out requiere una autorización explícita. "
            "Marcá la aprobación del late check-out antes de continuar con el check-out."
        )
    if context["requires_approval"] and normalized_mode != "late_approved":
        raise ValueError(
            "Este late check-out supera la cortesía y requiere aprobación del gerente. "
            "Derivalo a gerencia, o registrá el modo aprobado con motivo y cargo antes de completar."
        )
    if normalized_mode == "late_approved" and context["requires_approval"] and not normalized_reason:
        raise ValueError(
            "La aprobación de late check-out requiere un motivo. "
            "Escribí el motivo de la autorización antes de continuar."
        )

    try:
        normalized_fee = round(float(fee or 0), 2)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "El cargo de late check-out no es válido. "
            "Ingresá un monto numérico mayor o igual a cero."
        ) from exc
    if normalized_fee < 0:
        raise ValueError(
            "El cargo de late check-out no puede ser negativo. "
            "Ingresá un monto mayor o igual a cero."
        )
    return normalized_mode, normalized_fee, normalized_reason


def complete_check_out(
    booking_id: str,
    *,
    changed_by: str = "web",
    split_invoice: bool = False,
    ip_address: str = "",
    observations: str = "",
    payment_method: str = "",
    payment_ref: str = "",
    late_checkout_fee: float = 0,
    late_checkout_mode: str | None = None,
    late_checkout_approved: bool = False,
    late_checkout_reason: str = "",
    late_checkout_authorized: bool = False,
    discount: float = 0,
    discount_reason: str = "",
    damages_found: bool = False,
    keys_returned: bool = False,
    shift_id: str | None = None,
) -> dict[str, Any]:
    # ── Validate keys_returned BEFORE any database writes ──
    if not keys_returned:
        raise ValueError(
            "No se puede completar el check-out sin registrar la devolución de llaves. "
            "Marca 'Llaves devueltas' en el paso de verificación antes de cerrar la estancia."
        )

    db = get_database()

    # ── Validate folio has invoice if balance is pending ──
    folio = db.guest_folios.find_one(
        {"booking_id": booking_id},
        {"status": 1, "total_due": 1, "folio_number": 1},
    )
    if folio:
        folio_status = folio.get("status", "")
        total_due = round(float(folio.get("total_due", 0) or 0), 2)
        if folio_status == "open" and total_due > 0:
            existing_inv = db.reservation_invoices.find_one({"booking_id": booking_id}, {"_id": 1})
            if not existing_inv:
                raise ValueError(
                    f"No se puede completar el check-out: el folio {folio.get('folio_number', '')} "
                    f"tiene un saldo pendiente de ${total_due:.2f} sin factura generada. "
                    "Registra un pago para generar la factura antes de cerrar la estancia."
                )

    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "guest_name": 1, "guest_email": 1, "prop_id": 1, "is_test": 1,
         "check_in_date": 1, "check_out_date": 1, "total_price": 1, "currency": 1,
         "total_nights": 1, "rooms": 1, "room_type_id": 1, "assigned_rooms": 1,
         "check_out_room_inspected": 1, "check_out_keys_returned": 1, "stay_status": 1},
    )
    if booking is None:
        raise ValueError("Reserva no encontrada. Verificá el identificador de la reserva.")

    # ── Validate the stay is active: check-out only applies to checked-in stays ──
    # Una reserva que nunca registró check-in no tiene estancia que cerrar
    # (no-show, pendiente o sin estado). ``checked_out`` se permite aquí para
    # conservar el mensaje idempotente "already checked out" del update de abajo.
    stay_status_co = str(booking.get("stay_status") or "").strip().lower()
    if stay_status_co not in ("checked_in", "checked_out"):
        raise ValueError(
            f"No se puede completar el check-out: la reserva {booking_id} no tiene una estancia activa "
            f"(nunca registró check-in; estado actual: {stay_status_co or 'sin check-in'}). "
            "Hacé primero el check-in de la reserva o, si el huésped nunca llegó, "
            "marcala como no-show para cerrarla sin liquidación."
        )

    # ── Late check-out: ventana gobernada por la política (espejo de early) ──
    # La salida el día del check-out tras la hora se resuelve contra la política
    # del hotel. Dentro de la cortesía → ``late_courtesy`` sin cargo. Fuera de
    # ella → ``late_approved``: exige autorización gerencial
    # (``check-ins.late_checkout_approve``), motivo y cargo derivado del reloj.
    late_context = get_late_checkout_context(
        int(booking.get("prop_id", 0) or 0),
        str(booking.get("check_out_date", "") or ""),
        db=db,
    )
    if (
        str(late_checkout_mode or "").strip().lower() == "late_approved"
        and not late_checkout_authorized
    ):
        raise ValueError(
            "Permiso requerido: check-ins.late_checkout_approve. "
            "Solo un gerente de hotel o super_admin puede aprobar este late check-out: "
            "derivalo a gerencia para que lo autorice y complete la salida."
        )
    late_mode, late_fee, late_reason = validate_late_checkout(
        late_context,
        mode=late_checkout_mode,
        approved=late_checkout_approved,
        reason=late_checkout_reason,
        fee=late_checkout_fee,
    )

    changed_at = utc_now()
    # La hora/día REAL de salida se estampa en hora LOCAL del hotel (mismo
    # reloj que la política, la notificación ``actual_time`` y el check-in
    # ``check_in_time_actual``) — es el campo legible para recepción; guardarla
    # en UTC mezclaría relojes en el detalle de un late check-out.
    local_departure = local_now()

    checkout_set = {
        "stay_status": "checked_out",
        "updated_at": changed_at,
        "check_out_date_actual": local_departure.strftime("%Y-%m-%d"),
        "check_out_time_actual": local_departure.strftime("%H:%M"),
        "check_out_by": changed_by,
        "check_out_keys_returned": True,
    }
    if payment_method:
        checkout_set["check_out_payment_method"] = payment_method
    if payment_ref:
        checkout_set["check_out_payment_ref"] = payment_ref
    if late_mode:
        # El modo gobernado manda: el cargo derivado del reloj (o aprobado) es
        # el fee real del late check-out. ``check_out_late_checkout_fee`` es el
        # alias legacy que el detalle/UI ya leen.
        checkout_set.update({
            "check_out_mode": late_mode,
            "late_checkout_minutes": late_context["minutes_after"],
            "late_checkout_fee": late_fee,
            "check_out_late_checkout_fee": late_fee,
            "late_checkout_approved": True,
            "late_checkout_approved_by": changed_by,
            "late_checkout_approved_at": changed_at,
            "late_checkout_reason": late_reason,
            "late_checkout_policy_time": late_context["check_out_time"],
        })
    elif late_checkout_fee:
        # Ruta legacy: fee tipeado manualmente por recepción (sin ventana late).
        checkout_set["check_out_late_checkout_fee"] = round(late_checkout_fee, 2)
    if discount:
        checkout_set["check_out_discount"] = round(discount, 2)
    if discount_reason:
        checkout_set["check_out_discount_reason"] = discount_reason
    if damages_found:
        checkout_set["check_out_damages_found"] = True
    if observations:
        checkout_set["check_out_observations"] = observations
    if shift_id:
        # Front-desk check-outs are tied to the open cash shift at write time.
        checkout_set["shift_id"] = ObjectId(shift_id)

    result = db.booking_orders.find_one_and_update(
        {"booking_id": booking_id, "status": {"$nin": ["cancelled", "rejected"]}, "stay_status": "checked_in"},
        {"$set": checkout_set},
        projection={"_id": 0, "is_test": 1},
    )
    if result is None:
        existing = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "status": 1, "stay_status": 1})
        if existing is None:
            raise ValueError("Reserva no encontrada. Verificá el identificador de la reserva.")
        if existing.get("stay_status") == "checked_out":
            raise ValueError(
                "La reserva ya fue cerrada con check-out. "
                "No se puede repetir la operación: la estancia ya está liquidada."
            )
        raise ValueError(
            "No se puede completar el check-out desde el estado actual de la reserva "
            "(cancelada, rechazada o sin estancia activa). "
            "Hacé el check-in primero o contactá a gerencia."
        )

    audit_entry: dict[str, Any] = {
        "booking_id": booking_id, "status": "checked_out",
        "changed_at": changed_at, "reason": "front_desk_check_out",
        "changed_by": changed_by, "is_test": bool(result.get("is_test")),
        "check_out_method": "manual",
    }
    if ip_address:
        audit_entry["ip_address"] = ip_address
    if observations:
        audit_entry["observations"] = observations
    if payment_method:
        audit_entry["payment_method"] = payment_method
    if payment_ref:
        audit_entry["payment_ref"] = payment_ref
    if late_mode:
        audit_entry["check_out_mode"] = late_mode
        audit_entry["late_checkout_fee"] = round(late_fee, 2)
        audit_entry["late_checkout_minutes"] = late_context["minutes_after"]
        if late_reason:
            audit_entry["late_checkout_reason"] = late_reason
    elif late_checkout_fee:
        audit_entry["late_checkout_fee"] = round(late_checkout_fee, 2)
    if discount:
        audit_entry["discount"] = round(discount, 2)
        audit_entry["discount_reason"] = discount_reason
    if damages_found:
        audit_entry["damages_found"] = True
    db.booking_status_history.insert_one(audit_entry)

    # ── Audit log (universal) ──
    if booking and not booking.get("is_test"):
        try:
            register_action(
                prop_id=int(booking.get("prop_id", 0)),
                entity_type="reservation",
                entity_id=booking_id,
                action="check_out",
                summary=f"Check-out completado — {booking.get('guest_name', '')}",
                changed_by=changed_by,
                metadata={"guest_name": booking.get("guest_name", ""),
                         "payment_method": payment_method,
                         "observations": observations,
                         "damages_found": damages_found,
                         "keys_returned": keys_returned},
            )
        except Exception:
            logger.exception("Failed to register audit action for check-out %s", booking_id)

    # ── Notifications ──
    if booking:
        _notify_guest_check_out(booking_id, booking)
        if not booking.get("is_test"):
            _notify_staff_check_out(booking_id, booking)
            if late_mode in ("late_approved", "late_courtesy"):
                # El equipo (recepción/housekeeping) debe saber que la salida se
                # extendió y a qué hora real ocurrió (patrón notification_log
                # del check-in) — la habitación seguirá ocupada tras la hora de
                # política y la limpieza debe ajustarse. Aplica también a la
                # cortesía (sin cargo): la salida extendida afecta igual a la
                # limpieza aunque no haya fee.
                _notify_staff_window_extension(
                    booking_id,
                    booking,
                    window="late_checkout",
                    minutes=int(late_context.get("minutes_after", 0) or 0),
                    policy_time=str(late_context.get("check_out_time") or ""),
                    actual_time=local_now().strftime("%H:%M"),
                    fee=late_fee,
                    reason=late_reason,
                    mode=late_mode,
                )

    # ── Restore inventory ──
    if booking:
        try:
            _restore_inventory(
                prop_id=int(booking.get("prop_id", 0)),
                check_in_date=str(booking.get("check_in_date", "")),
                check_out_date=str(booking.get("check_out_date", "")),
                rooms=int(booking.get("rooms", 1)),
                room_type_id=str(booking.get("room_type_id", "")),
            )
            logger.info("Inventory restored for booking %s after check-out", booking_id)
        except Exception:
            logger.exception("Failed to restore inventory on check-out for booking %s", booking_id)

    # ── Post the clock-derived late check-out fee to the folio ──
    # El cargo se deriva de la política (gracia) + aprobación gerencial, nunca
    # del reloj del navegador; se publica en el folio como evento inmutable
    # (mismo patrón del early check-in) antes de liquidar y cerrar el folio.
    if booking and not booking.get("is_test") and late_fee > 0:
        try:
            from src.app.modules.billing.service import post_to_folio
            posted = post_to_folio(
                booking_id,
                category_id="late_checkout",
                concept=(
                    f"Late check-out autorizado — {late_context['minutes_after']} min "
                    f"después de las {late_context['check_out_time'] or 'hora de política'}"
                ),
                amount=late_fee,
                reference_id=f"{booking_id}:late_checkout",
                reference_type="late_checkout",
                shift_id=shift_id,
            )
            if posted is None:
                logger.error("Could not post late check-out fee for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to post late check-out fee for booking %s", booking_id)

    # ── Settle additional charges ──
    # El plegado de cargos a la factura principal (``update_invoice_additional_charges``)
    # reescribe la snapshot fiscal. Si la factura ya tiene pagos confirmados
    # (inmutable) y quedan cargos activos, NO se puede reescribir: en vez de
    # loguear y abandonar los cargos sin facturar, el fallback automático crea
    # la factura split de consumos (``create_split_charges_invoice``) para que
    # la conciliación cubra los cargos de todas formas.
    if booking and not booking.get("is_test"):
        try:
            if split_invoice:
                from src.app.modules.billing.service import create_split_charges_invoice
                charges_inv = create_split_charges_invoice(booking_id, changed_by=changed_by)
                if charges_inv:
                    logger.info("Split invoice created for booking %s", booking_id)
                else:
                    logger.info("No additional charges to split-invoice for booking %s", booking_id)
            else:
                from src.app.modules.billing.service import (
                    update_invoice_additional_charges,
                )
                try:
                    settled = update_invoice_additional_charges(booking_id, changed_by=changed_by)
                    if settled:
                        logger.info("Liquidated charges for booking %s", booking_id)
                    else:
                        logger.info("No invoice found to settle charges for booking %s", booking_id)
                except ValueError as exc:
                    # El módulo billing solo lanza ValueError por factura inmutable.
                    # Fallback automático SOLO cuando quedan cargos activos: si
                    # no hay nada que plegar, no se crea una split innecesaria.
                    immutable = _invoice_is_immutable(db, booking_id)
                    if immutable and _has_active_additional_charges(db, booking_id):
                        logger.warning(
                            "Invoice immutable for booking %s (%s) — falling back to split charges invoice",
                            booking_id,
                            exc,
                        )
                        from src.app.modules.billing.service import (
                            create_split_charges_invoice,
                        )
                        charges_inv = create_split_charges_invoice(booking_id, changed_by=changed_by)
                        if charges_inv:
                            logger.info("Split charges invoice created via fallback for booking %s", booking_id)
                        else:
                            logger.warning("Fallback split invoice returned nothing for booking %s", booking_id)
                    elif immutable:
                        logger.info(
                            "Invoice immutable and no active charges to settle for booking %s",
                            booking_id,
                        )
                    else:
                        raise
        except Exception:
            logger.exception("Failed to settle additional charges on check-out for booking %s", booking_id)

    # ── Complemento fiscal de postings de folio (decisión B) ──
    # Los postings de extensión / salida anticipada / late check-out viven en
    # el folio pero no en la factura principal: al cierre del checkout se emite
    # la complementaria (charges-only) que los cubre con total EXACTO al folio,
    # para que la factura del huésped siempre coincida con lo cobrado.
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.billing.service.lifecycle.invoices import create_folio_postings_complement_invoice
            comp = create_folio_postings_complement_invoice(booking_id, changed_by=changed_by)
            if comp:
                logger.info(
                    "Folio-postings complement invoice %s emitted at check-out for booking %s",
                    comp.get("invoice_number"), booking_id,
                )
        except Exception:
            logger.exception("Failed to emit folio-postings complement at check-out for booking %s", booking_id)

    # ── Mark rooms as dirty + auto-create cleaning tasks ──
    if booking:
        try:
            assigned_rooms_co: list[str] = booking.get("assigned_rooms") or []
            if assigned_rooms_co:
                room_docs_co = list(
                    db.hotel_rooms.find(
                        {"hotel_room_id": {"$in": assigned_rooms_co}},
                        {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1},
                    )
                )
                for r in room_docs_co:
                    label = r.get("room_label", "")
                    if not label:
                        continue
                    from src.app.modules.housekeeping.schemas import RoomStatusLogCreate
                    from src.app.modules.housekeeping.service.lifecycle.status import (
                        upsert_room_status,
                    )
                    upsert_room_status(RoomStatusLogCreate(
                        prop_id=booking["prop_id"],
                        room_type_id=r.get("room_type_id", ""),
                        room_label=label,
                        status="vacant_dirty",
                        note=f"Check-out: {booking_id}",
                    ))
                    db.housekeeping_tasks.insert_one({
                        "prop_id": booking["prop_id"],
                        "room_id": r["_id"],
                        "hotel_room_id": r.get("hotel_room_id", ""),
                        "room_label": label,
                        "room_type_id": r.get("room_type_id", ""),
                        "task_type": "cleaning",
                        "status": "pending",
                        "assigned_to": "",
                        "priority": "normal",
                        "note": f"Limpieza automática post check-out — reserva {booking_id}",
                        "scheduled_date": "",
                        "created_at": utc_now(),
                        "completed_at": None,
                    })
                logger.info("Rooms marked as dirty + cleaning tasks created for booking %s", booking_id)
        except Exception:
            logger.exception("Failed to mark rooms as dirty for booking %s", booking_id)

    # ── Register shift transaction ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.reception import register_transaction
            # Re-read the folio AFTER the late fee (and any additional-charge
            # settlement) was posted: the fetch at the top of the flow happened
            # BEFORE ``post_to_folio``, so its ``total_due`` would miss the late
            # fee and the shift report would under-collect. Use the fresh
            # total_due (room + charges - discounts - payments) instead of
            # booking.total_price which only reflects the original room rate.
            fresh_folio = db.guest_folios.find_one({"booking_id": booking_id})
            total_due = round(float(fresh_folio.get("total_due", 0) or 0), 2) if fresh_folio else float(booking.get("total_price", 0) or 0)
            register_transaction(
                prop_id=int(booking.get("prop_id", 0)),
                txn_type="check_out", booking_id=booking_id,
                amount=total_due, payment_method=payment_method or "",
                description=f"Check-out: {booking.get('guest_name', '')} — ${total_due:.2f}",
            )
        except Exception:
            logger.exception("Failed to register shift transaction for check-out %s", booking_id)

    # ── Close folio ──
    if booking and not booking.get("is_test"):
        try:
            from src.app.modules.billing.service import close_folio
            inv_doc = db.reservation_invoices.find_one({"booking_id": booking_id}, {"_id": 1})
            # Pass the ObjectId directly (canonical FK type): close_folio
            # also normalizes hex strings, but the source should not stringify
            # (audit 2026-08 — guest_folios.invoice_id was stored as str).
            inv_id = inv_doc["_id"] if inv_doc else None
            close_folio(booking_id, invoice_id=inv_id, closed_by=changed_by)
            logger.info("Folio closed for booking %s on check-out", booking_id)
        except Exception:
            logger.exception("Failed to close folio on check-out for booking %s", booking_id)

    # ── Notify guest about invoice ──
    if booking and not booking.get("is_test"):
        try:
            guest_email = (booking.get("guest_email") or "").strip()
            if guest_email:
                from src.app.modules.reservations.notifications import (
                    notify_guest_invoice,
                )
                inv = db.reservation_invoices.find_one(
                    {"booking_id": booking_id},
                    {"_id": 1, "invoice_number": 1, "total": 1},
                )
                if inv:
                    notify_guest_invoice(
                        booking_id=booking_id, guest_name=booking.get("guest_name", ""),
                        guest_email=guest_email, prop_id=int(booking.get("prop_id", 0)),
                        check_in_date=booking.get("check_in_date", ""),
                        check_out_date=booking.get("check_out_date", ""),
                        total_nights=int(booking.get("total_nights", 0)),
                        invoice_id=str(inv["_id"]), invoice_number=inv.get("invoice_number", ""),
                        invoice_total=float(inv.get("total", 0)), currency=booking.get("currency", "USD"),
                    )
        except Exception:
            logger.exception("Failed to notify guest about invoice on check-out for booking %s", booking_id)

    # ── Deactivate stay session ──
    if booking and not booking.get("is_test"):
        try:
            result_sess = db.stay_sessions.update_many(
                {"booking_id": booking_id, "active": True},
                {"$set": {"active": False, "deactivated_at": changed_at}},
            )
            if result_sess.modified_count > 0:
                logger.info("Stay session deactivated for booking %s on check-out", booking_id)
        except Exception:
            logger.exception("Failed to deactivate stay session for booking %s", booking_id)

    return {
        "booking_id": booking_id,
        "stay_status": "checked_out",
        "check_out_mode": late_mode or "normal",
        "late_checkout_fee": late_fee,
        "late_checkout_minutes": late_context["minutes_after"] if late_mode else 0,
    }
