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
REFUND_DOCUMENTS_COLLECTION = "refund_documents"
FACT_REFUND_DOCUMENTS = "fact_refund_documents"
FOLIO_SETTLEMENT_EVENTS = "folio_settlement_events"
FACT_FOLIO_SETTLEMENT_EVENTS = "fact_folio_settlement_events"

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
INDEXES_REFUND_DOCUMENTS = [
    IndexModel([("payment_id", ASCENDING)], name="idx_refund_doc_payment"),
    IndexModel([("invoice_id", ASCENDING)], name="idx_refund_doc_invoice"),
    IndexModel([("document_number", ASCENDING)], name="idx_refund_doc_number", unique=True),
    IndexModel([("prop_id", ASCENDING), ("issued_at", -1)], name="idx_refund_doc_prop_issued"),
]

INDEXES_FOLIO_SETTLEMENT_EVENTS = [
    IndexModel([("booking_id", ASCENDING), ("idempotency_key", ASCENDING)], name="idx_folio_settlement_booking_key", unique=True),
    IndexModel([("prop_id", ASCENDING), ("created_at", -1)], name="idx_folio_settlement_prop_created"),
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
    ensure_collection(FOLIO_SETTLEMENT_EVENTS, INDEXES_FOLIO_SETTLEMENT_EVENTS)
    ensure_collection(FACT_FOLIO_SETTLEMENT_EVENTS, INDEXES_FOLIO_SETTLEMENT_EVENTS)
    ensure_collection(REFUND_DOCUMENTS_COLLECTION, INDEXES_REFUND_DOCUMENTS)
    ensure_collection(FACT_REFUND_DOCUMENTS, INDEXES_REFUND_DOCUMENTS)


def module_status() -> ModuleStatus:
    from src.app.modules.billing.schemas import ModuleStatus
    return ModuleStatus(
        module="billing",
        status="active",
        description="Facturación/comprobantes (CU-O24) y pagos en línea (CU-O25).",
    )
