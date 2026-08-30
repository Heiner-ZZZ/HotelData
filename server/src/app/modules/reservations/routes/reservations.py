"""Reservations CRUD, search and report routes."""

from __future__ import annotations

import logging

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.app.core.types import to_json_safe
from src.app.modules.billing.schemas import PaymentCreate
from src.app.modules.billing.service import create_payment
from src.app.modules.reservations.routes.reservations_impl import (
    check_hotel_availability,
    export_reservations_csv,
    list_rate_plans_with_rates,
    preview_reservation,
    validate_rate_plan_eligibility,
)
from src.app.modules.reservations.schemas import (
    BookingListResponse,
    BookingResponse,
    ModuleStatus,
    PastStaysResponse,
    ReservationCreatedResponse,
)
from src.app.modules.reservations.service import (
    build_reservation_input,
    cancel_booking,
    confirm_booking,
    create_booking,
    get_booking_detail,
    get_check_in_status,
    get_reservation_stats,
    get_room_guests,
    list_reservation_dates,
    modify_booking,
    reject_booking,
    reservation_hotel_options,
    save_room_guests,
)
from src.app.modules.reservations.service.lifecycle.create import validate_coupon_code
from src.app.modules.reservations.service.pricing_backfill import (
    backfill_single_booking,
    list_unpriced_bookings,
)
from src.app.security.dependencies import require_permission, require_prop_permission
from src.app.security.hotel_filter import user_can_access_hotel
from src.app.security.role_helpers import get_role_name
from src.database.connection import get_database

_router_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modules/reservations", tags=["modules-reservations"])
api_router = APIRouter(prefix="/api/reservations", tags=["reservations-api"])


@router.get("/status", response_model=ModuleStatus)
def module_status_endpoint() -> ModuleStatus:
    return ModuleStatus(
        module="reservations", status="partial",
        description="Solicitudes de reserva con disponibilidad, precio, teléfono huésped, historial de estados, check-in/out manual sin pagos reales.",
    )


def _require_booking_same_hotel(db, booking_id: str, prop_id: int | None) -> None:
    """404 (no 403) si la reserva pertenece a otro hotel — deny cross-hotel.

    Usa el mensaje amigable canónico del módulo (contrato de UX).
    """
    doc = db.booking_orders.find_one({"booking_id": booking_id}, {"prop_id": 1})
    if doc is None or doc.get("prop_id") != prop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.",
        )


def _require_staff_prop_permission(db, current_user: dict, permission_code: str, prop_id: int | None) -> None:
    """Gate por-hotel INLINE para rutas mixtas (huésped/staff) de reservas.

    Flujo mixto: el huésped (``cliente``) accede a SUS reservas por ownership;
    el staff en contexto de hotel (``prop_id``) debe tener el permiso RESUELTO
    POR HOTEL (deny-by-default: el rol global no basta). Sin ``prop_id`` el
    staff conserva la vista multi-hotel global (super_admin/plataforma).
    """
    from src.app.security.permissions import user_has_permission
    from src.app.modules.hotels.service.operational import non_operational_hotel

    if get_role_name(current_user) == "cliente":
        return
    if prop_id is not None:
        if non_operational_hotel(db, prop_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"El hotel {prop_id} no está operativo.")
        if not user_can_access_hotel(current_user, prop_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Sin acceso al hotel {prop_id}.")
        if not user_has_permission(db, current_user, permission_code, prop_id=prop_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission_code}",
            )


@api_router.get("", response_model=BookingListResponse)
def reservations_list_api(
    page: int = Query(default=1, ge=1),
    created_date: str | None = Query(default=None, alias="date"),
    status: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    guest_name: str | None = Query(default=None),
    folio: str | None = Query(default=None),
    stay_status: str | None = Query(default=None, alias="stay_status"),
    booking_source: str | None = Query(default=None, alias="booking_source"),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    from src.app.modules.reservations.service.queries import list_bookings as _list
    _require_staff_prop_permission(get_database(), current_user, "reservations.read", prop_id)
    return BookingListResponse.model_validate(to_json_safe(_list(page=page, page_size=20, created_date=created_date, status=status, prop_id=prop_id, guest_name=guest_name, folio=folio, stay_status=stay_status, booking_source=booking_source, user=current_user)))


@api_router.get("/dates")
def reservation_dates_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    return list_reservation_dates(prop_id=prop_id, user=current_user)


@api_router.get("/past-stays", response_model=PastStaysResponse)
def reservations_past_stays_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """Zona "Estadías pasadas" del huésped — solo lectura.

    Devuelve los bookings terminados del usuario (check-out, no-show o fechas
    vencidas) con ``read_only_reason`` que explica por qué no hay acciones.
    El scope ``cliente`` es ownership estricto por FK ``user_id``. Declarada
    ANTES del catch-all ``/{booking_id}`` para que no lo capture.
    """
    from src.app.modules.reservations.service.queries import list_past_stays as _past
    return PastStaysResponse.model_validate(to_json_safe(_past(prop_id=prop_id, user=current_user)))


@api_router.get("/options")
def reservations_options_api(current_user: dict = Depends(require_permission("reservations.read"))):
    return {"hotel_options": reservation_hotel_options(user=current_user)}


@api_router.get("/availability-check")
def reservation_availability_check_api(
    prop_id: int = Query(..., ge=1),
    check_in: str = Query(...),
    check_out: str = Query(...),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    """Check if a hotel has room types and inventory available for a given date range."""
    return check_hotel_availability(prop_id, check_in, check_out)


@api_router.get("/rate-plans")
def available_rate_plans_api(
    prop_id: int = Query(..., ge=1),
    check_in: str = Query(...),
    check_out: str = Query(...),
    room_type_id: str = Query(default=""),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    """Return available rate plans for a hotel + date range + optional room type."""
    return list_rate_plans_with_rates(prop_id, check_in, check_out, room_type_id)


@api_router.post("/preview")
def reservation_preview_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    _check_body_prop_id(query_prop_id, payload)
    return preview_reservation(payload)


@api_router.post("", status_code=status.HTTP_201_CREATED, response_model=ReservationCreatedResponse)
def reservations_create_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.create")),
):
    try:
        _check_body_prop_id(query_prop_id, payload)
        user_role = get_role_name(current_user)
        elig_error = validate_rate_plan_eligibility(payload, user_role)
        if elig_error:
            raise ValueError(elig_error)
        if not payload.get("created_by"):
            payload["created_by"] = current_user.get("username", "web")
        if not payload.get("user_id"):
            # FK to users._id — store the raw ObjectId (canonical format).
            # ``build_reservation_input`` normalizes any hex string later.
            payload["user_id"] = current_user.get("_id")
        reservation_input = build_reservation_input(payload, source=get_role_name(current_user))
        from src.app.modules.reservations.service.validation import (
            validate_booking_form_requirements,
        )
        form_errors = validate_booking_form_requirements(reservation_input)
        if form_errors:
            raise ValueError("; ".join(form_errors))
        if reservation_input.rate_plan_id:
            payload["rate_plan_id"] = reservation_input.rate_plan_id
        # Canal WEB (huésped reservando online): esta ruta (/reservations) es
        # el motor de reserva web. NO exige ni estampa turno de caja activo —
        # el turno es un requisito SOLO de las operaciones físicas en
        # recepción (POST /management/manual-reservations y check-in/out),
        # que sí pasan por get_active_shift_id. La reserva web queda con
        # shift_id null (contrato de reception/shifts.get_active_shift_id:
        # "Web-channel bookings keep shift_id null").
        prop_id = int(payload.get("prop_id") or 0)
        if prop_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere un prop_id válido para registrar la reserva.",
            )
        shift_id = None

        # ── Depósito real (política de pago por adelantado) ──
        # El wizard de recepción registra el depósito mínimo en la MISMA
        # llamada: se valida contra la política del hotel en create_booking
        # (``deposit_amount``) y se persiste como pago real de billing con el
        # shift_id del turno activo — nunca un stub que marque "paid" en
        # falso.
        deposit = payload.get("deposit") or {}
        deposit_amount = None
        deposit_method = None
        deposit_reference = None
        if deposit:
            try:
                deposit_amount = round(float(deposit.get("amount") or 0), 2)
                deposit_method = str(deposit.get("method") or "").strip() or None
                deposit_reference = str(deposit.get("reference") or "").strip() or None
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El depósito debe incluir un monto numérico válido.",
                )
            if deposit_amount <= 0 or not deposit_method:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El depósito debe incluir un monto mayor a cero y un método de pago.",
                )

        booking = create_booking(
            reservation_input,
            shift_id=shift_id,
            deposit_amount=deposit_amount,
        )
        if deposit_amount is not None:
            payment = create_payment(
                PaymentCreate(
                    booking_id=booking["booking_id"],
                    amount=deposit_amount,
                    method=deposit_method,
                ),
                shift_id=shift_id,
                reference=deposit_reference or f"DEP-{booking['booking_id']}",
                actor_user_id=current_user.get("_id"),
                actor_username=current_user.get("username"),
                payment_source="deposit",
            )
            if payment is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No se pudo registrar el depósito: la reserva no existe.",
                )
            if payment.get("status") == "failed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "El depósito no pudo confirmarse contra el folio. "
                        "Registralo desde Facturación para completar la reserva."
                    ),
                )
        return ReservationCreatedResponse.model_validate(to_json_safe(booking))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/validate-coupon")
def validate_coupon_api(
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    _check_body_prop_id(query_prop_id, payload)
    coupon_code = payload.get("coupon_code") or payload.get("promo_code")
    prop_id = payload.get("prop_id")
    if not coupon_code:
        raise HTTPException(
            status_code=400,
            detail="El código promocional es obligatorio. Ingresalo para validarlo.",
        )
    if not prop_id:
        raise HTTPException(
            status_code=400,
            detail="El hotel es obligatorio para validar el código. Seleccioná un hotel e intentá de nuevo.",
        )
    # Campos opcionales para validación de relación correcta (tarifa/habitación/fechas)
    check_in = payload.get("check_in") or payload.get("checkInDate")
    check_out = payload.get("check_out") or payload.get("checkOutDate")
    rate_plan_id = payload.get("rate_plan_id") or payload.get("ratePlanId")
    room_type_id = payload.get("room_type_id") or payload.get("room_type")
    error, discount, _ = validate_coupon_code(
        coupon_code,
        int(prop_id),
        check_in=check_in,
        check_out=check_out,
        rate_plan_id=rate_plan_id,
        room_type_id=room_type_id,
    )
    return {"valid": error is None, "message": error or "Código válido", "discount_percent": discount or 0}


@api_router.get("/stats")
def reservation_stats_api(current_user: dict = Depends(require_permission("reservations.read"))):
    return get_reservation_stats(user=current_user)


@api_router.get("/export")
def reservation_export_api(
    format: str = Query(default="csv"),
    status_filter: str | None = Query(default=None, alias="status"),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    output, raw_date = export_reservations_csv(status_filter=status_filter, prop_id=prop_id)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=reservas_{raw_date}.csv",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@api_router.get("/unpriced")
def reservations_unpriced_api(
    current_user: dict = Depends(require_permission("reservations.update")),
):
    """Bookings sin ``total_price`` para el banner 'Recalcular precio' del admin.

    Vista de mantenimiento (staff): lista las reservas sin precio del hotel
    (o de todos, si super_admin), respetando ``hotel_filter_from_user``.
    Requiere ``reservations.update`` porque alimenta una acción de escritura.
    Registrada ANTES de ``/{booking_id}`` para que el literal ``unpriced``
    no lo capture la ruta de detalle.
    """
    db = get_database()
    return list_unpriced_bookings(db, user=current_user, limit=50)


def _check_body_prop_id(query_prop_id: int | None, payload: dict) -> None:
    """Consistencia gate(query) ↔ body: el prop_id del query es autoritativo."""
    try:
        body_prop_id = int(str(payload.get("prop_id") or 0))
    except (TypeError, ValueError):
        body_prop_id = 0
    if query_prop_id is not None and body_prop_id != query_prop_id:
        raise HTTPException(status_code=400, detail="prop_id del query y del body no coinciden")


@api_router.get("/{booking_id}", response_model=BookingResponse)
def reservation_detail_api(
    booking_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_permission("reservations.read")),
):
    """Booking detail with embedded reservation history.

    Flujo MIXTO (migración E): el huésped (``cliente``) lee su propia reserva
    (check de ownership inline); el staff en contexto de hotel (``prop_id``)
    pasa por el gate por-hotel INLINE (``reservations.read`` resuelto por
    role_assignment → hotel_roles) + 404 si la reserva es de otro hotel.
    """
    from src.app.security.permissions import user_has_permission
    db = get_database()
    if get_role_name(current_user) == "cliente":
        booking = db.booking_orders.find_one({"booking_id": booking_id}, {"user_id": 1})
        user_id = current_user.get("_id")
        if isinstance(user_id, str) and ObjectId.is_valid(user_id):
            user_id = ObjectId(user_id)
        booking_user_id = (booking or {}).get("user_id")
        if isinstance(booking_user_id, str) and ObjectId.is_valid(booking_user_id):
            booking_user_id = ObjectId(booking_user_id)
        if booking is None or user_id is None or booking_user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta reserva.")
    else:
        # Staff: deny-by-default por hotel. Con prop_id → el rol del hotel
        # (role_assignment → hotel_roles) debe portar reservations.read; la
        # reserva debe pertenecer al hotel pedido (404 cross-hotel). Sin
        # prop_id (super_admin/plataforma multi-hotel) conserva la vista global.
        if query_prop_id is not None:
            from src.app.modules.hotels.service.operational import non_operational_hotel as _non_op
            if _non_op(db, query_prop_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"El hotel {query_prop_id} no está operativo.")
            if not user_can_access_hotel(current_user, query_prop_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Sin acceso al hotel {query_prop_id}.")
            if not user_has_permission(db, current_user, "reservations.read", prop_id=query_prop_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso requerido: reservations.read")
            booking = db.booking_orders.find_one({"booking_id": booking_id}, {"prop_id": 1})
            if booking is None or booking.get("prop_id") != query_prop_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")

    detail = get_booking_detail(booking_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.",
        )
    # Flatten booking fields to top-level for BookingResponse validation
    data = {**detail.get("booking", {}), **detail}
    data.pop("booking", None)
    return BookingResponse.model_validate(to_json_safe(data))


@api_router.patch("/{booking_id}/special-requests")
def reservation_special_request_status_api(
    booking_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    """Flip one checklist item's fulfillment status (pending ↔ fulfilled).

    Body: ``{"kind": "special_request" | "amenity", "label": "Cama extra",
    "status": "fulfilled"}``. ``kind`` defaults to ``special_request`` for
    backward compatibility. Returns the normalized fulfillment list after the
    update, with the ``fulfilled_at`` date on fulfilled entries.
    """
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    from src.app.modules.reservations.service.special_request_fulfillment import (
        update_amenity_fulfillment,
        update_special_request_fulfillment,
    )

    label = str(payload.get("label") or "").strip()
    status_value = str(payload.get("status") or "").strip()
    kind = str(payload.get("kind") or "special_request").strip()
    if not label or not status_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="label y status son requeridos.")
    try:
        if kind == "amenity":
            updated = update_amenity_fulfillment(booking_id, label, status_value)
        else:
            updated = update_special_request_fulfillment(booking_id, label, status_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True, "kind": kind, "fulfillment": updated}


@api_router.get("/{booking_id}/cancel-preview")
def reservation_cancel_preview_api(
    booking_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    """Preview cancellation penalty without actually cancelling."""
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    from src.app.core.timezone import local_today
    from src.app.modules.reservations.service.cleanup import (
        _calculate_cancellation_penalty,
    )

    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.",
        )
    if booking.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=(
                "Solo se pueden previsualizar cancelaciones de reservas pendientes; "
                "esta reserva está en estado '" + str(booking.get("status", "")) + "'. "
                "Contactá a recepción para gestionar la cancelación."
            ),
        )
    today_str = local_today()
    if today_str >= (booking.get("check_in_date") or ""):
        raise HTTPException(status_code=400, detail="No se puede cancelar una reserva cuya fecha de entrada ya ha comenzado o pasado.")

    penalty = _calculate_cancellation_penalty(
        prop_id=int(booking.get("prop_id", 0)),
        check_in_date=booking.get("check_in_date", ""),
        total_price=booking.get("total_price"),
        total_nights=int(booking.get("total_nights", 0)),
        room_type_id=booking.get("room_type_id", ""),
    )

    total_price = booking.get("total_price") or 0
    total_nights = int(booking.get("total_nights") or 0)
    one_night_price = round(float(total_price) / max(total_nights, 1), 2)

    return {
        "booking_id": booking_id,
        "guest_name": booking.get("guest_name", ""),
        "check_in_date": booking.get("check_in_date", ""),
        "total_price": booking.get("total_price"),
        "currency": booking.get("currency", "USD"),
        "total_nights": total_nights,
        "one_night_price": one_night_price,
        "free_cancellation": penalty["free_cancellation"],
        "penalty_percent": penalty["penalty_percent"],
        "penalty_amount": penalty["penalty_amount"],
        "hours_until_checkin": penalty["hours_until_checkin"],
        "cancellation_hours": penalty["cancellation_hours"],
    }


@api_router.post("/{booking_id}/cancel")
def reservation_cancel_api(
    booking_id: str,
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.delete")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    try:
        return cancel_booking(booking_id, reason=str(payload.get("reason") or "cancelled_by_user"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "web")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/confirm")
def reservation_confirm_api(
    booking_id: str,
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    role = get_role_name(current_user)
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede confirmar reservas.")
    try:
        return confirm_booking(booking_id, reason=str(payload.get("reason") or "confirmed_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/reject")
def reservation_reject_api(
    booking_id: str,
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    role = get_role_name(current_user)
    if role not in ("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el staff del hotel puede rechazar reservas.")
    try:
        return reject_booking(booking_id, reason=str(payload.get("reason") or "rejected_by_staff"),
            changed_by=str(payload.get("changed_by") or current_user.get("username", "staff")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.post("/{booking_id}/recalculate-price")
def reservation_recalculate_price_api(
    booking_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    """Recalcula el precio de una reserva sin ``total_price`` (botón del admin).

    Reutiliza ``backfill_single_booking`` — el MISMO path que el script
    ``migrate_backfill_booking_prices.py`` — así el botón de la UI y la
    migración masiva producen resultados idénticos (precio canónico,
    penalizaciones y folio).

    - 200 con ``already_priced`` → la reserva ya tenía precio (no-op).
    - 200 con ``skipped=unpricable`` → sin tarifa calculable (no escribe).
    - 404 → la reserva no existe.
    - 403 → la reserva pertenece a un hotel fuera del alcance del usuario
      (``user_can_access_hotel``) — mismo hardening que el GET /unpriced.
    """
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "prop_id": 1},
    )
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.",
        )
    prop_id = int(booking.get("prop_id", 0) or 0)
    if not user_can_access_hotel(current_user, prop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a las reservas de este hotel.",
        )
    result = backfill_single_booking(db, booking_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró la reserva. Verificá el número de reserva e intentá de nuevo.",
        )
    return result


@api_router.patch("/{booking_id}", response_model=BookingResponse)
def reservation_modify_api(
    booking_id: str,
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    try:
        return BookingResponse.model_validate(to_json_safe(modify_booking(booking_id,
            check_in_date=str(payload["check_in_date"]) if payload.get("check_in_date") else None,
            check_in_time=str(payload["check_in_time"]) if payload.get("check_in_time") else None,
            check_out_date=str(payload["check_out_date"]) if payload.get("check_out_date") else None,
            room_type_id=str(payload["room_type_id"]) if payload.get("room_type_id") else None,
            rooms=int(payload["rooms"]) if payload.get("rooms") is not None else None,
            comment=str(payload["comment"]) if payload.get("comment") is not None else None,
            changed_by=current_user.get("username", "web"),
            selected_amenities=payload.get("selected_amenities"))))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}/room-guests")
def room_guests_get_api(
    booking_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    return get_room_guests(booking_id)


@api_router.put("/{booking_id}/room-guests")
def room_guests_put_api(
    booking_id: str,
    payload: dict = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.update")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    try:
        return save_room_guests(booking_id, payload.get("room_guests", []))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@api_router.get("/{booking_id}/check-in-status")
def check_in_status_api(
    booking_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_prop_permission("reservations.read")),
):
    _require_booking_same_hotel(get_database(), booking_id, query_prop_id)
    return get_check_in_status(booking_id)
