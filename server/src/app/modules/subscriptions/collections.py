"""Colecciones e índices de suscripciones y pagos (PLAN_SUSCRIPCION_Y_PAGOS.md §5)."""

from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, IndexModel

from src.database.collections import ensure_collection

SUBSCRIPTIONS_COLLECTION = "subscriptions"
SUBSCRIPTION_INVOICES_COLLECTION = "subscription_invoices"
SUBSCRIPTION_PAYMENTS_COLLECTION = "subscription_payments"
PAYMENT_METHODS_COLLECTION = "payment_methods"

INDEXES_SUBSCRIPTIONS = [
    IndexModel([("prop_id", ASCENDING)], name="idx_sub_prop", unique=True),
    IndexModel([("status", ASCENDING)], name="idx_sub_status"),
    IndexModel([("renews_at", ASCENDING)], name="idx_sub_renews"),
]
INDEXES_SUBSCRIPTION_INVOICES = [
    IndexModel(
        [("subscription_id", ASCENDING), ("created_at", DESCENDING)],
        name="idx_sinv_sub_created",
    ),
    IndexModel(
        [("prop_id", ASCENDING), ("status", ASCENDING)],
        name="idx_sinv_prop_status",
    ),
    IndexModel([("invoice_number", ASCENDING)], name="idx_sinv_number", unique=True),
]
INDEXES_SUBSCRIPTION_PAYMENTS = [
    IndexModel(
        [("status", ASCENDING), ("created_at", ASCENDING)],
        name="idx_spay_status_created",
    ),
    IndexModel([("subscription_id", ASCENDING)], name="idx_spay_sub"),
    IndexModel([("invoice_id", ASCENDING)], name="idx_spay_invoice"),
]
INDEXES_PAYMENT_METHODS = [
    IndexModel([("code", ASCENDING)], name="idx_pm_code", unique=True),
    IndexModel([("sort_order", ASCENDING)], name="idx_pm_sort"),
]


def ensure_subscription_collections() -> None:
    ensure_collection(SUBSCRIPTIONS_COLLECTION, INDEXES_SUBSCRIPTIONS)
    ensure_collection(SUBSCRIPTION_INVOICES_COLLECTION, INDEXES_SUBSCRIPTION_INVOICES)
    ensure_collection(SUBSCRIPTION_PAYMENTS_COLLECTION, INDEXES_SUBSCRIPTION_PAYMENTS)
    ensure_collection(PAYMENT_METHODS_COLLECTION, INDEXES_PAYMENT_METHODS)
