from __future__ import annotations
from typing import TYPE_CHECKING

from pymongo import IndexModel, ASCENDING

from src.database.collections import ensure_collection

if TYPE_CHECKING:
    from src.app.modules.billing.schemas import ModuleStatus

INVOICES_COLLECTION = "reservation_invoices"
PAYMENTS_COLLECTION = "reservation_payments"
FACT_INVOICES = "fact_reservation_invoices"
FACT_PAYMENTS = "fact_reservation_payments"
FOLIO_COLLECTION = "guest_folios"

INDEXES_INVOICES = [
    IndexModel([("booking_id", ASCENDING)], name="idx_inv_booking"),
    IndexModel([("invoice_number", ASCENDING)], name="idx_inv_number", unique=True),
    IndexModel([("status", ASCENDING)], name="idx_inv_status"),
]
INDEXES_PAYMENTS = [
    IndexModel([("booking_id", ASCENDING)], name="idx_pay_booking"),
    IndexModel([("invoice_id", ASCENDING)], name="idx_pay_invoice"),
    IndexModel([("status", ASCENDING)], name="idx_pay_status"),
    IndexModel([("prop_id", ASCENDING), ("paid_at", -1)], name="idx_pay_prop_paid_at"),
]
INDEXES_FOLIOS = [
    IndexModel([("booking_id", ASCENDING)], name="idx_fl_booking", unique=True),
    IndexModel([("folio_number", ASCENDING)], name="idx_fl_number", unique=True),
    IndexModel([("prop_id", ASCENDING)], name="idx_fl_prop"),
    IndexModel([("status", ASCENDING)], name="idx_fl_status"),
    IndexModel([("created_at", -1)], name="idx_fl_created_desc"),
    IndexModel([("prop_id", ASCENDING), ("created_at", -1)], name="idx_fl_prop_created_desc"),
]


def ensure_billing_collections() -> None:
    ensure_collection(INVOICES_COLLECTION, INDEXES_INVOICES)
    ensure_collection(PAYMENTS_COLLECTION, INDEXES_PAYMENTS)
    ensure_collection(FACT_INVOICES, INDEXES_INVOICES)
    ensure_collection(FACT_PAYMENTS, INDEXES_PAYMENTS)
    ensure_collection(FOLIO_COLLECTION, INDEXES_FOLIOS)


def module_status() -> ModuleStatus:
    from src.app.modules.billing.schemas import ModuleStatus
    return ModuleStatus(
        module="billing",
        status="active",
        description="Facturación/comprobantes (CU-O24) y pagos simulados (CU-O25).",
    )
