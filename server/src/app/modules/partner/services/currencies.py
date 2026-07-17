from __future__ import annotations

import logging
from typing import Any

from src.database.connection import get_database

logger = logging.getLogger(__name__)

# ── Default currencies seed (12 LATAM + 4 global) ──────────────────────────
_DEFAULT_CURRENCIES: list[dict[str, Any]] = [
    {"code": "USD", "name": "Dólar estadounidense", "symbol": "$", "decimals": 2, "active": True},
    {"code": "MXN", "name": "Peso mexicano", "symbol": "$", "decimals": 2, "active": True},
    {"code": "EUR", "name": "Euro", "symbol": "€", "decimals": 2, "active": True},
    {"code": "COP", "name": "Peso colombiano", "symbol": "$", "decimals": 0, "active": True},
    {"code": "PEN", "name": "Sol peruano", "symbol": "S/", "decimals": 2, "active": True},
    {"code": "CLP", "name": "Peso chileno", "symbol": "$", "decimals": 0, "active": True},
    {"code": "ARS", "name": "Peso argentino", "symbol": "$", "decimals": 2, "active": True},
    {"code": "BRL", "name": "Real brasileño", "symbol": "R$", "decimals": 2, "active": True},
    {"code": "CRC", "name": "Colón costarricense", "symbol": "₡", "decimals": 2, "active": True},
    {"code": "GTQ", "name": "Quetzal guatemalteco", "symbol": "Q", "decimals": 2, "active": True},
    {"code": "DOP", "name": "Peso dominicano", "symbol": "RD$", "decimals": 2, "active": True},
    {"code": "PAB", "name": "Balboa panameño", "symbol": "B/.", "decimals": 2, "active": True},
    {"code": "GBP", "name": "Libra esterlina", "symbol": "£", "decimals": 2, "active": True},
    {"code": "JPY", "name": "Yen japonés", "symbol": "¥", "decimals": 0, "active": True},
    {"code": "CAD", "name": "Dólar canadiense", "symbol": "C$", "decimals": 2, "active": True},
    {"code": "BOB", "name": "Boliviano", "symbol": "Bs.", "decimals": 2, "active": True},
]


def _ensure_index() -> None:
    """Create unique index on code field if it doesn't exist."""
    db = get_database()
    try:
        db.system_currencies.create_index("code", unique=True)
    except Exception as exc:
        logger.warning("Could not create system_currencies index: %s", exc)


def seed_default_currencies() -> int:
    """Insert default currencies if they don't already exist.

    Called automatically by list_currencies() on first access.
    Returns the number of currencies inserted.
    """
    db = get_database()
    _ensure_index()
    inserted = 0
    for cur in _DEFAULT_CURRENCIES:
        existing = db.system_currencies.find_one({"code": cur["code"]})
        if existing is None:
            db.system_currencies.insert_one(dict(cur))
            inserted += 1
    if inserted:
        logger.info("Seeded %d default currencies", inserted)
    return inserted


# ── CRUD ────────────────────────────────────────────────────────────────────

def list_currencies(active_only: bool = False) -> list[dict[str, Any]]:
    """Return all currencies, seeding defaults on first access."""
    db = get_database()
    seed_default_currencies()
    query: dict[str, Any] = {}
    if active_only:
        query["active"] = True
    results = list(db.system_currencies.find(query, {"_id": 0}).sort("code", 1))
    return results


def currency_by_code(code: str) -> dict[str, Any] | None:
    """Get a single currency by ISO 4217 code (case-insensitive)."""
    db = get_database()
    return db.system_currencies.find_one({"code": code.upper().strip()}, {"_id": 0})


def save_currency(
    *,
    code: str,
    name: str = "",
    symbol: str = "$",
    decimals: int | None = None,
    active: bool = True,
) -> dict[str, Any]:
    """Create or update a currency.

    The ``decimals`` parameter is treated carefully: 0 is a valid value
    (e.g. JPY, CLP, COP), so we only fall back to 2 when it's None.
    """
    db = get_database()
    clean_code = code.upper().strip()
    if not clean_code or len(clean_code) != 3:
        raise ValueError("Currency code must be a 3-letter ISO 4217 code")

    # decimals: 0 is valid (CLP, COP, JPY, etc.)
    final_decimals: int
    if decimals is not None:
        final_decimals = max(0, min(int(decimals), 4))
    else:
        final_decimals = 2

    existing = db.system_currencies.find_one({"code": clean_code})

    doc = {
        "code": clean_code,
        "name": name.strip() if name else "",
        "symbol": symbol.strip() if symbol else "$",
        "decimals": final_decimals,
        "active": bool(active),
    }

    if existing is None:
        db.system_currencies.insert_one(doc)
    else:
        db.system_currencies.update_one({"code": clean_code}, {"$set": doc})

    return db.system_currencies.find_one({"code": clean_code}, {"_id": 0}) or doc


def toggle_currency_active(code: str) -> dict[str, Any] | None:
    """Flip the ``active`` flag. Returns the updated document or None if not found."""
    db = get_database()
    cur = db.system_currencies.find_one({"code": code.upper().strip()})
    if cur is None:
        return None
    new_active = not cur.get("active", True)
    db.system_currencies.update_one(
        {"code": code.upper().strip()},
        {"$set": {"active": new_active}},
    )
    return db.system_currencies.find_one({"code": code.upper().strip()}, {"_id": 0})


def delete_currency(code: str) -> bool:
    """Delete a currency permanently.

    Raises ValueError if any property in dim_hotels references this currency.
    Returns True if deleted, False if not found.
    """
    db = get_database()
    clean_code = code.upper().strip()
    cur = db.system_currencies.find_one({"code": clean_code})
    if cur is None:
        return False

    # Referential integrity: don't delete if any property uses this currency
    ref_count = db.dim_hotels.count_documents({
        "$or": [
            {"currency": clean_code},
            {"accepted_currencies": {"$regex": clean_code}},
        ]
    })
    if ref_count > 0:
        raise ValueError(
            f"No se puede eliminar {clean_code}: está referenciada por {ref_count} propiedad(es). "
            "Desactívala en su lugar."
        )

    db.system_currencies.delete_one({"code": clean_code})
    return True
