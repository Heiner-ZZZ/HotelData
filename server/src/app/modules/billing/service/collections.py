from __future__ import annotations

from pymongo import IndexModel, ASCENDING, DESCENDING

from src.database.collections import ensure_collection

INVOICES_COLLECTION = "reservation_invoices"
PAYMENTS_COLLECTION = "reservation_payments"
FACT_INVOICES = "fact_reservation_invoices"
FACT_PAYMENTS = "fact_reservation_payments"

INDEXES_INVOICES = [
    IndexModel([("booking_id", ASCENDING)], name="idx_inv_booking"),
    IndexModel([("invoice_number", ASCENDING)], name="idx_inv_number", unique=True),
    IndexModel([("status", ASCENDING)], name="idx_inv_status"),
]
INDEXES_PAYMENTS = [
    IndexModel([("booking_id", ASCENDING)], name="idx_pay_booking"),
    IndexModel([("invoice_id", ASCENDING)], name="idx_pay_invoice"),
    IndexModel([("status", ASCENDING)], name="idx_pay_status"),
]


def ensure_billing_collections() -> None:
    ensure_collection(INVOICES_COLLECTION, INDEXES_INVOICES)
    ensure_collection(PAYMENTS_COLLECTION, INDEXES_PAYMENTS)
    ensure_collection(FACT_INVOICES, INDEXES_INVOICES)
    ensure_collection(FACT_PAYMENTS, INDEXES_PAYMENTS)


def module_status() -> ModuleStatus:
    from src.app.modules.billing.schemas import ModuleStatus
    return ModuleStatus(
        module="billing",
        status="active",
        description="Facturación/comprobantes (CU-O24) y pagos simulados (CU-O25).",
    )
