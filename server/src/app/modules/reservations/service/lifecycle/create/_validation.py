"""Deposit and coupon validation logic."""

from __future__ import annotations


from src.database.connection import get_database


def _validate_deposit(
    prop_id: int,
    total_price: float | None,
    season_id: str = "",
    room_type_id: str = "",
    manual_reservation: bool = False,
) -> str | None:
    """Check if the hotel policy requires a minimum deposit.

    Returns an error message if a deposit is required but not met,
    or None if the booking passes validation.
    """
    if manual_reservation:
        return None
    db = get_database()
    policy_filter: dict[str, object] = {"prop_id": prop_id}
    if room_type_id:
        policy_filter["room_type_id"] = room_type_id
    else:
        policy_filter["room_type_id"] = {"$in": ["", None]}
    if season_id:
        policy_filter["season_id"] = season_id
    else:
        policy_filter["season_id"] = {"$in": ["", None]}
    policy = db.hotel_policies.find_one(
        policy_filter,
        {"_id": 0, "deposit_required": 1, "deposit_percent": 1},
    )
    if not policy:
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "season_id": {"$in": ["", None]}},
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
        "Por favor, proporcione la garantía correspondiente."
    )


def validate_coupon_code(coupon_code: str, prop_id: int) -> tuple[str | None, int | None]:
    if not coupon_code:
        return None, None
    db = get_database()
    code = coupon_code.strip().upper()
    coupon = db.coupon_codes.find_one({"coupon_code": code, "prop_id": prop_id, "is_active": True})
    if not coupon:
        coupon = db.coupon_codes.find_one({"coupon_code": code, "is_active": True})
        if not coupon:
            return f"Código promocional '{coupon_code}' no válido.", None
        campaign = db.promotion_campaigns.find_one({"campaign_id": coupon.get("campaign_id")})
        if campaign:
            campaign_prop = campaign.get("prop_id")
            if campaign_prop and int(campaign_prop) != prop_id:
                return "Este código no aplica para este hotel.", None

    discount_percent = coupon.get("discount_percent", 0)
    if not discount_percent or discount_percent <= 0:
        return "El código promocional no tiene un descuento válido.", None
    return None, int(discount_percent)
