"""Deposit and coupon validation logic."""

from __future__ import annotations

from bson import ObjectId

from src.database.connection import get_database


def get_deposit_policy(
    prop_id: int,
    rate_plan_id: str = "",
    room_type_id: str = "",
) -> dict | None:
    """Resolve the deposit policy for a property.

    Hierarchy: rate-plan-specific > room-type-specific > hotel-wide.
    Returns a dict with ``deposit_required`` and ``deposit_percent`` keys,
    or None when the property has no deposit policy row. Shared by the
    booking-creation validation, the reservation preview and the check-in
    gate so the three never drift apart.
    """
    db = get_database()
    policy = None
    # 1. Rate-plan-specific
    if rate_plan_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "rate_plan_id": rate_plan_id},
            {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
        )
    # 2. Room-type-specific
    if not policy and room_type_id:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
        )
    # 3. Hotel-wide fallback
    if not policy:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
        )
    return policy


def _validate_deposit(
    prop_id: int,
    total_price: float | None,
    season_id: str = "",
    room_type_id: str = "",
    rate_plan_id: str = "",
    manual_reservation: bool = False,
    deposit_amount: float | None = None,
) -> str | None:
    """Check if the hotel policy requires a minimum deposit.

    Checks rate-plan-specific policies first, then room-type, then hotel-wide.
    Returns an error message if a deposit is required but not met,
    or None if the booking passes validation.

    ``deposit_amount`` is the REAL deposit payment registered in the same
    call (billing ``create_payment``, shift-gated): a deposit policy is
    satisfied only by actual money recorded against the booking — never by
    the legacy fake card-processing stub that marked bookings as "paid"
    without persisting anything.
    """
    if manual_reservation:
        return None
    policy = get_deposit_policy(prop_id, rate_plan_id=rate_plan_id, room_type_id=room_type_id)
    if not policy:
        return None
    deposit_required = policy.get("deposit_required", False)
    deposit_percent = int(policy.get("deposit_percent", 0) or 0)
    if not deposit_required or deposit_percent <= 0:
        return None
    if total_price is None or total_price <= 0:
        return "No se puede calcular el depósito mínimo: precio total no disponible."
    min_deposit = round(total_price * deposit_percent / 100, 2)
    if deposit_amount is not None and deposit_amount >= min_deposit - 0.01:
        return None
    if deposit_amount is not None:
        return (
            f"El depósito registrado (${deposit_amount:.2f}) no alcanza el mínimo "
            f"del {deposit_percent}% (${min_deposit:.2f}) que esta propiedad exige "
            "para confirmar la reserva."
        )
    return (
        f"Esta propiedad requiere un depósito mínimo del {deposit_percent}% "
        f"(${min_deposit:.2f}) para confirmar la reserva. "
        "Registrá el depósito o contactá a recepción para completarla."
    )


def validate_coupon_code(
    coupon_code: str,
    prop_id: int,
    check_in: str | None = None,
    check_out: str | None = None,
    rate_plan_id: str | None = None,
    room_type_id: str | None = None,
) -> tuple[str | None, int | None, ObjectId | None]:
    """Validate a coupon code and return (error, discount_percent, coupon_id).

    coupon_id is the ObjectId FK to coupon_codes._id, or None if invalid.

    Además de is_active/prop_id, valida:
    - Ventana de vigencia de la campaña (start_date/end_date vs check_in)
    - Relación correcta tarifa↔habitación: si la campaña limita a tarifas específicas
      (applicable_rate_plan_ids), la tarifa elegida debe estar en la lista; y
      si se dan tarifa+h abit ación, la tarifa debe cubrir esa habitación
      (rate_plans.applicable_room_types / room_type_id).
    """
    if not coupon_code:
        return None, None, None
    db = get_database()
    code = coupon_code.strip().upper()
    # Un cupón retirado (is_deleted=True) jamás vuelve a validar: el flag se
    # conserva por trazabilidad al reducir coupon_count, pero queda inerte.
    coupon = db.coupon_codes.find_one(
        {"coupon_code": code, "prop_id": prop_id, "is_active": True, "is_deleted": {"$ne": True}}
    )
    if not coupon:
        coupon = db.coupon_codes.find_one({"coupon_code": code, "is_active": True, "is_deleted": {"$ne": True}})
        if not coupon:
            return (
                f"El código promocional '{coupon_code}' no es válido. "
                "Revisá el código e intentá de nuevo, o continuá sin promoción."
            ), None, None
        campaign = db.promotion_campaigns.find_one({"campaign_id": coupon.get("campaign_id")})
        if campaign:
            campaign_prop = campaign.get("prop_id")
            if campaign_prop and int(campaign_prop) != prop_id:
                return (
                    "Este código no aplica para este hotel. Usá un código válido para "
                    "este hotel o continuá sin promoción."
                ), None, None
    else:
        campaign = db.promotion_campaigns.find_one({"campaign_id": coupon.get("campaign_id")})

    # Si no hay campaña (cupón huérfano), solo valida descuento
    if not coupon:
        return (
            f"El código promocional '{coupon_code}' no es válido. "
            "Revisá el código e intentá de nuevo, o continuá sin promoción."
        ), None, None

    # Re-obtener campaña si no se obtuvo arriba (caso prop_id match directo)
    if 'campaign' not in locals() or campaign is None:
        campaign = db.promotion_campaigns.find_one({"campaign_id": coupon.get("campaign_id")})

    # ── Validación de vigencia por fechas ──
    if campaign and (check_in or check_out):
        start = (campaign.get("start_date") or "").strip()
        end = (campaign.get("end_date") or "").strip()
        # Solo valida si la campaña define ventana
        if start or end:
            # Usa check_in como fecha de referencia (si no hay check_in, usa check_out)
            ref_date = (check_in or check_out or "").strip()
            if ref_date:
                # ISO YYYY-MM-DD lexicográfico válido
                if start and ref_date < start:
                    return (
                        f"Este código aún no está vigente. Es válido desde {start}. "
                        "Probá con otro código o continuá sin promoción."
                    ), None, None
                if end and ref_date > end:
                    return (
                        f"Este código venció el {end} o está fuera de la ventana de la promoción. "
                        "Probá con otro código o continuá sin promoción."
                    ), None, None
                # Si hay rango completo, también valida que TODA la estadía esté dentro
                if start and end and check_in and check_out:
                    if check_in < start or check_out > end:
                        # Para estricto, la estadía debe estar contenida; si no, mensaje genérico
                        if check_in < start:
                            return (
                                f"Este código aún no está vigente. Es válido desde {start}. "
                                "Probá con otro código o continuá sin promoción."
                            ), None, None
                        if check_out > end:
                            return (
                                f"Este código solo es válido para estadías hasta {end}. "
                                "Ajustá las fechas o continuá sin promoción."
                            ), None, None

    # ── Validación de tarifa/habitación relacionada ──
    if campaign is not None:
        applicable_plans = campaign.get("applicable_rate_plan_ids")
        # None / missing / [] => aplica a todo el hotel (sin restricción)
        if isinstance(applicable_plans, list) and len(applicable_plans) > 0 and rate_plan_id:
            if rate_plan_id not in applicable_plans:
                return (
                    "Este código no aplica para la tarifa seleccionada. Elegí una tarifa "
                    "incluida en la promoción o continuá sin promoción."
                ), None, None
        # Si la tarifa y habitación se dan, verificar que la tarifa cubra esa habitación
        if rate_plan_id and room_type_id:
            plan = db.rate_plans.find_one({"rate_plan_id": rate_plan_id, "prop_id": prop_id}, {"applicable_room_types": 1, "room_type_id": 1})
            if plan is not None:
                app_types = plan.get("applicable_room_types") or []
                single = plan.get("room_type_id") or ""
                if room_type_id not in app_types and single != room_type_id:
                    return (
                        "La tarifa seleccionada no corresponde a la habitación elegida. "
                        "Elegí una tarifa válida para esa habitación o continuá sin promoción."
                    ), None, None

    discount_percent = coupon.get("discount_percent", 0)
    if not discount_percent or discount_percent <= 0:
        return (
            "El código promocional no tiene un descuento válido. "
            "Probá con otro código o continuá sin promoción."
        ), None, None
    return None, int(discount_percent), coupon["_id"]
