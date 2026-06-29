"""Corporate/negotiated rate contracts.

Each contract represents a negotiated pricing agreement between a property
and a company. Contracts support two pricing models:

- **Percentage discount**: ``discount_percent`` off the standard calendar rate.
- **Fixed rate**: ``fixed_rate`` per night, overriding the calendar rate entirely.

Both models can optionally be scoped to specific ``rate_plan_id`` s and/or
``room_type_id`` s. When empty lists, the negotiated pricing applies to all
plans/room types of the property.

Contracts are identified by a unique ``contract_code`` that the company uses
when making a reservation.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc, safe_bool, slugify
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.properties import partner_hotel_detail
from src.database.connection import get_database


def _validate_contract_dates(start_date: str, end_date: str) -> None:
    """Validate date range for a contract."""
    try:
        sd = date_type.fromisoformat(start_date) if start_date else None
        ed = date_type.fromisoformat(end_date) if end_date else None
    except (ValueError, TypeError):
        raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD.")
    if sd and ed and sd > ed:
        raise ValueError("La fecha de inicio no puede ser mayor a la fecha de fin.")


def _build_contract_id(prop_id: int, company_name: str) -> str:
    """Generate a unique contract ID."""
    return f"CC-{prop_id}-{slugify(company_name)}"


def create_corporate_contract(
    prop_id: int,
    *,
    company_name: str,
    contract_code: str,
    description: str = "",
    discount_percent: int = 0,
    fixed_rate: float = 0.0,
    applicable_rate_plan_ids: list[str] | None = None,
    applicable_room_type_ids: list[str] | None = None,
    start_date: str = "",
    end_date: str = "",
    is_active: Any = True,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Create or update a corporate contract for a property."""
    detail = partner_hotel_detail(prop_id)
    if detail is None:
        return None

    clean_company = clean_text(company_name)
    if not clean_company:
        raise ValueError("Debe indicar el nombre de la empresa.")
    clean_code = clean_text(contract_code)
    if not clean_code:
        raise ValueError("Debe indicar un código de contrato.")
    if len(clean_code) > 50:
        raise ValueError("El código de contrato no puede superar 50 caracteres.")

    discount = int(discount_percent or 0)
    fixed = float(fixed_rate or 0)
    if discount < 0 or discount > 100:
        raise ValueError("El descuento debe ser entre 0% y 100%.")
    if fixed < 0:
        raise ValueError("La tarifa fija no puede ser negativa.")
    if discount > 0 and fixed > 0:
        raise ValueError("No puede combinarse descuento porcentual con tarifa fija. Elija solo uno.")
    if discount == 0 and fixed == 0:
        raise ValueError("Debe indicar un descuento porcentual o una tarifa fija.")

    _validate_contract_dates(start_date, end_date)

    db = get_database()
    contract_id = _build_contract_id(prop_id, clean_company)
    clean_desc = clean_text(description)
    clean_start = clean_text(start_date)
    clean_end = clean_text(end_date)

    # Validate contract_code uniqueness per property
    existing_same_code = db.corporate_contracts.find_one(
        {"prop_id": prop_id, "contract_code": clean_code, "contract_id": {"$ne": contract_id}},
        {"_id": 1},
    )
    if existing_same_code:
        raise ValueError(f"El código de contrato '{clean_code}' ya existe en esta propiedad.")

    payload = {
        "contract_id": contract_id,
        "prop_id": prop_id,
        "company_name": clean_company,
        "contract_code": clean_code.upper(),
        "description": clean_desc,
        "discount_percent": discount,
        "fixed_rate": round(fixed, 2),
        "applicable_rate_plan_ids": applicable_rate_plan_ids or [],
        "applicable_room_type_ids": applicable_room_type_ids or [],
        "start_date": clean_start,
        "end_date": clean_end,
        "is_active": safe_bool(is_active),
        "updated_at": now_utc(),
    }
    document = db.corporate_contracts.find_one_and_update(
        {"contract_id": contract_id},
        {"$set": payload, "$setOnInsert": {"created_at": now_utc()}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_action(
        prop_id=prop_id,
        entity_type="corporate_contract",
        entity_id=contract_id,
        action="create",
        summary=f"Contrato corporativo '{clean_company}' creado — desc: {discount}%, fijo: ${fixed:.2f}",
        changed_by=changed_by,
        metadata={"company_name": clean_company, "contract_code": clean_code, "discount_percent": discount, "fixed_rate": fixed},
    )
    return document


def update_corporate_contract(
    contract_id: str,
    *,
    company_name: str,
    contract_code: str,
    description: str = "",
    discount_percent: int = 0,
    fixed_rate: float = 0.0,
    applicable_rate_plan_ids: list[str] | None = None,
    applicable_room_type_ids: list[str] | None = None,
    start_date: str = "",
    end_date: str = "",
    is_active: Any = True,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Update an existing corporate contract."""
    db = get_database()
    existing = db.corporate_contracts.find_one(
        {"contract_id": contract_id},
        {"_id": 0, "prop_id": 1, "company_name": 1},
    )
    if existing is None:
        return None
    prop_id = existing["prop_id"]

    clean_company = clean_text(company_name)
    if not clean_company:
        raise ValueError("Debe indicar el nombre de la empresa.")
    clean_code = clean_text(contract_code)
    if not clean_code:
        raise ValueError("Debe indicar un código de contrato.")

    discount = int(discount_percent or 0)
    fixed = float(fixed_rate or 0)
    if discount < 0 or discount > 100:
        raise ValueError("El descuento debe ser entre 0% y 100%.")
    if fixed < 0:
        raise ValueError("La tarifa fija no puede ser negativa.")
    if discount > 0 and fixed > 0:
        raise ValueError("No puede combinarse descuento porcentual con tarifa fija.")
    if discount == 0 and fixed == 0:
        raise ValueError("Debe indicar un descuento porcentual o una tarifa fija.")

    _validate_contract_dates(start_date, end_date)

    # Validate contract_code uniqueness (excluding self)
    dup = db.corporate_contracts.find_one(
        {"prop_id": prop_id, "contract_code": clean_code, "contract_id": {"$ne": contract_id}},
        {"_id": 1},
    )
    if dup:
        raise ValueError(f"El código de contrato '{clean_code}' ya existe en esta propiedad.")

    payload = {
        "company_name": clean_company,
        "contract_code": clean_code.upper(),
        "description": clean_text(description),
        "discount_percent": discount,
        "fixed_rate": round(fixed, 2),
        "applicable_rate_plan_ids": applicable_rate_plan_ids or [],
        "applicable_room_type_ids": applicable_room_type_ids or [],
        "start_date": clean_text(start_date),
        "end_date": clean_text(end_date),
        "is_active": safe_bool(is_active),
        "updated_at": now_utc(),
    }
    document = db.corporate_contracts.find_one_and_update(
        {"contract_id": contract_id},
        {"$set": payload},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    register_action(
        prop_id=prop_id,
        entity_type="corporate_contract",
        entity_id=contract_id,
        action="update",
        summary=f"Contrato corporativo '{clean_company}' actualizado",
        changed_by=changed_by,
        metadata={"contract_code": clean_code, "discount_percent": discount, "fixed_rate": fixed},
    )
    return document


def delete_corporate_contract(contract_id: str, changed_by: str = "system") -> dict[str, Any] | None:
    """Delete a corporate contract."""
    db = get_database()
    existing = db.corporate_contracts.find_one(
        {"contract_id": contract_id},
        {"_id": 0, "prop_id": 1, "company_name": 1},
    )
    if existing is None:
        return None
    db.corporate_contracts.delete_one({"contract_id": contract_id})
    register_action(
        prop_id=existing["prop_id"],
        entity_type="corporate_contract",
        entity_id=contract_id,
        action="delete",
        summary=f"Contrato corporativo '{existing.get('company_name', contract_id)}' eliminado",
        changed_by=changed_by,
    )
    return {"contract_id": contract_id, "deleted": True}


def list_corporate_contracts(
    prop_id: int | None = None,
    is_active: bool | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List corporate contracts with optional filters."""
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id is not None:
        query["prop_id"] = prop_id
    if is_active is not None:
        query["is_active"] = is_active
    items = list(
        db.corporate_contracts.find(query, {"_id": 0})
        .sort([("company_name", 1)])
        .limit(limit)
    )
    for item in items:
        item["rate_label"] = _contract_rate_label(item)
    return items


def _contract_rate_label(contract: dict[str, Any]) -> str:
    """Human-readable label for the contract's pricing."""
    if contract.get("fixed_rate", 0) > 0:
        return f"${contract['fixed_rate']:.2f}/noche (fijo)"
    pct = contract.get("discount_percent", 0)
    return f"{pct}% descuento"


def validate_contract_code(
    contract_code: str,
    prop_id: int,
    *,
    rate_plan_id: str = "",
    room_type_id: str = "",
) -> tuple[str | None, dict[str, Any] | None]:
    """Validate a corporate contract code and return contract data if valid.

    Returns (error_message, contract) tuple. When valid, contract contains
    ``discount_percent`` and/or ``fixed_rate`` for pricing adjustments.
    """
    if not contract_code:
        return None, None
    db = get_database()
    code = contract_code.strip().upper()
    contract = db.corporate_contracts.find_one(
        {"prop_id": prop_id, "contract_code": code, "is_active": True},
        {"_id": 0},
    )
    if not contract:
        return f"Código de contrato '{contract_code}' no válido.", None

    # Check date validity
    today = date_type.today().isoformat()
    start = contract.get("start_date", "")
    end = contract.get("end_date", "")
    if start and today < start:
        return "El contrato aún no está vigente.", None
    if end and today > end:
        return "El contrato ha expirado.", None

    # Check applicable rate plans
    applicable_plans = contract.get("applicable_rate_plan_ids", [])
    if applicable_plans and rate_plan_id and rate_plan_id not in applicable_plans:
        return "Este contrato no aplica para el plan tarifario seleccionado.", None

    # Check applicable room types
    applicable_rooms = contract.get("applicable_room_type_ids", [])
    if applicable_rooms and room_type_id and room_type_id not in applicable_rooms:
        return "Este contrato no aplica para el tipo de habitación seleccionado.", None

    return None, contract


def apply_contract_pricing(
    total_price: float | None,
    total_nights: int,
    contract: dict[str, Any] | None,
) -> tuple[float | None, str | None]:
    """Apply corporate contract pricing to a total price.

    Returns (adjusted_price, pricing_source) where pricing_source is one of
    ``\"corporate_discount\"``, ``\"corporate_fixed\"``, or None.
    """
    if not contract or total_price is None:
        return total_price, None

    fixed = float(contract.get("fixed_rate", 0) or 0)
    if fixed > 0 and total_nights > 0:
        return round(fixed * total_nights, 2), "corporate_fixed"

    pct = int(contract.get("discount_percent", 0) or 0)
    if pct > 0:
        discounted = round(total_price * (1 - pct / 100), 2)
        return discounted, "corporate_discount"

    return total_price, None
