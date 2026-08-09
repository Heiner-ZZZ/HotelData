"""Tests for the explicit Vendor AP service boundary."""
from __future__ import annotations

from bson import ObjectId


def test_vendor_ap_service_requires_hotel_scope_and_never_mixes_properties(db):
    from src.app.modules.expenses.service.vendor_ap import list_vendor_bills

    first = ObjectId()
    second = ObjectId()
    db.expense_invoices.insert_many([
        {"_id": first, "prop_id": 1, "vendor_name": "Proveedor A", "status": "pending", "total": 10.0},
        {"_id": second, "prop_id": 2, "vendor_name": "Proveedor B", "status": "pending", "total": 900.0},
    ])

    result = list_vendor_bills(prop_id=1)

    assert result["total"] == 1
    assert result["items"][0]["prop_id"] == 1
    assert result["items"][0]["vendor_name"] == "Proveedor A"


def test_vendor_ap_service_rejects_missing_property_scope():
    from src.app.modules.expenses.service.vendor_ap import list_vendor_bills

    try:
        list_vendor_bills(prop_id=0)
    except ValueError as exc:
        assert "prop_id" in str(exc)
    else:
        raise AssertionError("Vendor AP must require a positive hotel scope")
