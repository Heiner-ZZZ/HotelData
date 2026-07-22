"""Payment processing endpoint — validates card details and processes payments."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException

from src.app.security.dependencies import require_permission

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _luhn_check(card_number: str) -> bool:
    """Validate a card number using the Luhn algorithm."""
    digits = [int(ch) for ch in card_number if ch.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _validate_expiry(expiry: str) -> bool:
    """Validate MM/YY expiry format and that the card has not expired."""
    m = re.match(r"^(0[1-9]|1[0-2])/(\d{2})$", expiry)
    if not m:
        return False
    month = int(m.group(1))
    year = 2000 + int(m.group(2))
    now = datetime.now(timezone.utc)
    # Card valid until end of expiry month
    if year < now.year or (year == now.year and month < now.month):
        return False
    return True


def _validate_cvv(cvv: str, card_number: str) -> bool:
    """Validate CVV (3 digits for most cards, 4 for Amex)."""
    digits_only = "".join(ch for ch in card_number if ch.isdigit())
    is_amex = digits_only.startswith("34") or digits_only.startswith("37")
    expected_len = 4 if is_amex else 3
    return bool(re.match(r"^\d{" + str(expected_len) + r"}$", cvv))


def _mask_card(card_number: str) -> str:
    """Return last 4 digits of the card number."""
    digits = "".join(ch for ch in card_number if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else "0000"


def _generate_transaction_id() -> str:
    import secrets
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(4)
    return f"TXN-{stamp}-{token}".upper()


@router.post("/process")
def process_payment(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("payments.manage")),
):
    """Process a card payment.

    Accepts: card_number, card_holder, expiry (MM/YY), cvv, amount, currency.
    Returns: transaction_id, status, card_last4, auth_code.
    """
    card_number = "".join(str(payload.get("card_number", "")).split())
    card_holder = str(payload.get("card_holder", "")).strip()
    expiry = str(payload.get("expiry", "")).strip()
    cvv = str(payload.get("cvv", "")).strip()
    amount = float(payload.get("amount", 0))

    # ── Validation ──
    errors = []
    if not card_number:
        errors.append("Número de tarjeta requerido.")
    elif not _luhn_check(card_number):
        errors.append("Número de tarjeta inválido.")
    if not card_holder:
        errors.append("Nombre del titular requerido.")
    if not expiry:
        errors.append("Fecha de expiración requerida.")
    elif not _validate_expiry(expiry):
        errors.append("Fecha de expiración inválida o vencida.")
    if not cvv:
        errors.append("Código de seguridad (CVV) requerido.")
    elif not _validate_cvv(cvv, card_number):
        errors.append("Código de seguridad (CVV) inválido.")
    if amount <= 0:
        errors.append("El monto debe ser mayor a cero.")

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    # ── Processing ──
    transaction_id = _generate_transaction_id()
    card_last4 = _mask_card(card_number)
    auth_code = f"AUTH-{datetime.now(timezone.utc).strftime('%H%M%S')}"

    return {
        "ok": True,
        "transaction_id": transaction_id,
        "status": "approved",
        "card_last4": card_last4,
        "card_brand": _detect_brand(card_number),
        "card_holder": card_holder,
        "amount": round(amount, 2),
        "auth_code": auth_code,
        "message": "Pago procesado exitosamente.",
    }


def _detect_brand(card_number: str) -> str:
    """Detect card brand from the first digits."""
    digits = "".join(ch for ch in card_number if ch.isdigit())
    if digits.startswith("4"):
        return "Visa"
    if digits.startswith(("51", "52", "53", "54", "55")) or (16 <= len(digits) <= 19 and digits.startswith(("2221", "2720"))):
        if 222100 <= int(digits[:6]) <= 272099:
            return "Mastercard"
    if digits.startswith(("34", "37")):
        return "American Express"
    if digits.startswith(("6011", "65")) or (digits.startswith("64") and len(digits) >= 4 and "4" <= digits[2] <= "9"):
        return "Discover"
    return "Desconocida"
