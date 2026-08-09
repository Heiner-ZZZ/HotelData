"""Vendor AP service boundary.

Vendor bills are hotel liabilities, not guest invoices. This module keeps the
public service contract explicit while reusing the existing Mongo source of
truth during the modular-monolith transition.
"""
from __future__ import annotations

import math
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from src.app.core.types import to_json_safe
from src.database.connection import get_database

COLLECTION = "expense_invoices"


def _require_prop_id(prop_id: int) -> int:
    prop_id = int(prop_id)
    if prop_id < 1:
        raise ValueError("prop_id es obligatorio para Vendor AP")
    return prop_id


def _enrich(doc: dict[str, Any]) -> dict[str, Any]:
    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    return to_json_safe(result)


def list_vendor_bills(
    *,
    prop_id: int,
    status: str | None = None,
    vendor: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List supplier bills for exactly one hotel."""
    prop_id = _require_prop_id(prop_id)
    if page < 1 or page_size < 1 or page_size > 100:
        raise ValueError("Paginación Vendor AP inválida")
    query: dict[str, Any] = {"prop_id": prop_id}
    if status:
        query["status"] = {"$in": [part.strip() for part in status.split(",") if part.strip()]}
    if vendor:
        query["vendor_name"] = {"$regex": vendor.strip(), "$options": "i"}
    db = get_database()
    total = db[COLLECTION].count_documents(query)
    cursor = (
        db[COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [_enrich(doc) for doc in cursor],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
        "has_next": page * page_size < total,
        "has_prev": page > 1,
        "prop_id": prop_id,
    }


def get_vendor_bill(*, prop_id: int, invoice_id: str) -> dict[str, Any] | None:
    """Get one supplier bill only when its property FK matches."""
    prop_id = _require_prop_id(prop_id)
    try:
        oid = ObjectId(invoice_id)
    except (InvalidId, TypeError):
        return None
    doc = get_database()[COLLECTION].find_one({"_id": oid, "prop_id": prop_id})
    return _enrich(doc) if doc else None


def vendor_ap_summary(prop_id: int) -> dict[str, Any]:
    """Return approved, paid, unpaid and count metrics for one hotel."""
    prop_id = _require_prop_id(prop_id)
    db = get_database()
    rows = list(db[COLLECTION].find(
        {"prop_id": prop_id},
        {"status": 1, "total": 1},
    ))
    approved = round(sum(float(row.get("total", 0) or 0) for row in rows if row.get("status") in {"approved", "paid"}), 2)
    paid = round(sum(float(row.get("total", 0) or 0) for row in rows if row.get("status") == "paid"), 2)
    return {
        "prop_id": prop_id,
        "approved": approved,
        "paid": paid,
        "unpaid": round(approved - paid, 2),
        "pending_count": sum(1 for row in rows if row.get("status") == "pending"),
        "total_count": len(rows),
    }
