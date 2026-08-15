"""Deposit and coupon validation logic."""

from __future__ import annotations

from bson import ObjectId

from src.database.connection import get_database


def _validate_deposit(
    prop_id: int,
    total_price: float | None,
    season_id: str = "",
    room_type_id: str = "",
    rate_plan_id: str = "",
    manual_reservation: bool = False,
) -> str | None:
    """Check if the hotel policy requires a minimum deposit.

    Checks rate-plan-specific policies first, then room-type, then hotel-wide.
    Returns an error message if a deposit is required but not met,
    or None if the booking passes validation.
    """
    if manual_reservation:
        return None
    db = get_database()
    # Hierarchy: rate_plan > room_type > hotel-wide
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
    if not policy:
        return None
    deposit_required = policy.get("deposit_required", False)
    deposit_percent = int(policy.get("deposit_percent", 0) or 0)
    if not deposit_required or deposit_percent <= 0:
        return None
    if total_price is None or total_price <= 0:
        return "No se puede calcular el depósito mínimo: precio total no disponible."
    min_deposit = round(total_price * deposit_percent / 100, 2)
    return (
        f"Esta propiedad requiere un depósito mínimo del {deposit_percent}% "
        f"(${min_deposit:.2f}) para confirmar la reserva. "
        "Ingresá la garantía correspondiente o contactá a recepción para completarla."
    )


def validate_coupon_code(coupon_code: str, prop_id: int) -> tuple[str | None, int | None, ObjectId | None]:
    """Validate a coupon code and return (error, discount_percent, coupon_id).

    coupon_id is the ObjectId FK to coupon_codes._id, or None if invalid.
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

    discount_percent = coupon.get("discount_percent", 0)
    if not discount_percent or discount_percent <= 0:
        return (
            "El código promocional no tiene un descuento válido. "
            "Probá con otro código o continuá sin promoción."
        ), None, None
    return None, int(discount_percent), coupon["_id"]
