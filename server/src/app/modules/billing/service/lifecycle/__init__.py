"""Billing lifecycle package — split into focused submodules."""

from __future__ import annotations

from src.app.modules.billing.service.lifecycle._helpers import (
    _enrich_invoice,
    _enrich_payment,
    _find_booking,
    _fmt,
    _generate_invoice_number,
    _now,
    _update_both,
    _write_both,
    FACT_INVOICES,
    FACT_PAYMENTS,
    INVOICES,
    PAYMENTS,
)
from src.app.modules.billing.service.lifecycle.invoices import (
    _record_earnings,
    add_line_item,
    cancel_invoice,
    create_invoice,
    reconstruct_historical_invoice_for_folio,
    reconcile_positive_invoice_accounting,
    generate_invoice_for_booking,
    get_invoice,
    get_invoice_stats,
    list_invoices,
    remove_line_item,
    repair_cancelled_or_refunded_invoice,
    update_invoice_additional_charges,
    create_split_charges_invoice,
    create_complement_invoice,
)
from src.app.modules.billing.service.lifecycle.payments import (
    create_payment,
    get_payment,
    list_payments,
    link_payment_to_shift,
    refund_payment,
    classify_failed_payment_informational,
)
from src.app.modules.billing.service.lifecycle.refunds import (
    create_credit_note_for_invoice,
    ensure_refund_document_for_payment,
)
from src.app.modules.billing.service.lifecycle.analytics import (
    get_invoice_dashboard,
    get_payments_dashboard,
)

__all__ = [
    "add_line_item",
    "cancel_invoice",
    "create_invoice",
    "reconstruct_historical_invoice_for_folio",
    "reconcile_positive_invoice_accounting",
    "create_payment",
    "generate_invoice_for_booking",
    "get_invoice",
    "get_invoice_stats",
    "get_payment",
    "list_invoices",
    "list_payments",
    "link_payment_to_shift",
    "refund_payment",
    "classify_failed_payment_informational",
    "remove_line_item",
    "repair_cancelled_or_refunded_invoice",
    "update_invoice_additional_charges",
    "create_split_charges_invoice",
    "create_complement_invoice",
    "get_invoice_dashboard",
    "get_payments_dashboard",
    "create_credit_note_for_invoice",
    "ensure_refund_document_for_payment",
]
