"""Pin the wire-shape invariants of the Fase #5 expenses ``*Response`` classes.

These tests interrogate the Pydantic models directly — no HTTP round-trip —
because the underlying invariant is the model itself: ``ObjectIdStr`` +
``AliasChoices`` + ``populate_by_name`` MUST turn raw Mongo ``_id``
ObjectIds into plain string ``id`` on the wire, MUST enforce pagination
envelopes (booleans, not truthy strings), MUST accept permissive
``list[Any]`` payloads for nested aggregates, and MUST preserve nested
``dict[str, Any]`` blocks (with bool values) verbatim under
``extra="allow"``.

If any of these assertions fails after a future refactor, the wire shape
of ``/api/expenses/*`` will silently drift — the test serves as a tripwire.

Mirrors ``tests/test_billing_responses.py`` and the
``TestObjectIdStrKeepInSync`` pattern in ``test_partner_history.py``.
"""
from __future__ import annotations

import pytest
from bson import ObjectId

from src.app.modules.expenses.routes import (
    DashboardResponse,
    InvoiceListResponse,
    InvoiceResponse,
    TrialBalanceResponse,
)


# ──────────────────────────── Tests ────────────────────────────


class TestInvoiceResponseIdCoercion:
    """Invariant #1: ``id: ObjectIdStr`` must coerce ``bson.ObjectId`` → plain ``str``.

    Without the BeforeValidator in ``core/types.py``, ``id`` would serialize
    as ``{\"$oid\": \"...\"}`` (FastAPI's default for ObjectId), which the
    Angular frontend cannot parse as a plain string. This test fails the
    moment someone removes the alias chain.
    """

    def test_object_id_in_underscore_id_becomes_plain_string(self):
        oid = ObjectId()
        doc = {
            "_id": oid,
            "vendor_name": "Distribuidora Lima",
            "category": "Bebidas",
            "description": "Compra mensual",
            "amount": 100.0,
            "tax_amount": 16.0,
            "total": 116.0,
            "status": "pending",
            "prop_id": 1,
            "invoice_date": "2024-01-01",
            "due_date": "2024-01-15",
            "notes": "test invoice",
            "created_at": "2024-01-01T12:00:00",
        }
        model = InvoiceResponse.model_validate(doc)
        # ObjectIdStr BeforeValidator turned ObjectId into str.
        assert isinstance(model.id, str), (
            f"id must be str on the wire, got {type(model.id).__name__}: {model.id!r}"
        )
        assert model.id == str(oid)
        assert len(model.id) == 24
        # No MongoDB-shape leakage on the wire representation.
        assert "$oid" not in model.id

    def test_string_in_underscore_id_passes_through_unchanged(self):
        """Pre-stringified ``_id`` (list-enrich path) must not double-coerce."""
        existing_str = str(ObjectId())
        doc = {
            "_id": existing_str,
            "vendor_name": "Acme",
            "category": "Snacks",
            "amount": 50.0,
            "tax_amount": 0.0,
            "status": "approved",
            "prop_id": 1,
        }
        model = InvoiceResponse.model_validate(doc)
        assert model.id == existing_str

    def test_id_field_through_alias_id_via_populate_by_name(self):
        """``populate_by_name=True`` allows construction via the wire name ``id``."""
        wire_doc = {
            "id": str(ObjectId()),
            "vendor_name": "Vendor X",
            "category": "Other",
            "amount": 10.0,
            "tax_amount": 0.0,
            "status": "paid",
            "prop_id": 1,
        }
        model = InvoiceResponse.model_validate(wire_doc)
        assert model.id == wire_doc["id"]


class TestInvoiceListResponsePaginationFlags:
    """Invariant #2: envelope returns ``has_next`` and ``has_prev`` as plain booleans.

    Locks the pagination shape so frontend list components can rely on
    these keys being present and properly typed, regardless of upstream
    service-side computation drift.
    """

    def test_envelope_carries_pagination_flags(self):
        envelope = {
            "items": [
                {
                    "_id": ObjectId(),
                    "vendor_name": "Vendor A",
                    "category": "Bebidas",
                    "amount": 30.0,
                    "tax_amount": 0.0,
                    "total": 30.0,
                    "status": "approved",
                    "prop_id": 1,
                },
                {
                    "_id": ObjectId(),
                    "vendor_name": "Vendor B",
                    "category": "Snacks",
                    "amount": 90.0,
                    "tax_amount": 14.4,
                    "total": 104.4,
                    "status": "pending",
                    "prop_id": 1,
                },
            ],
            "total": 50,
            "page": 2,
            "page_size": 20,
            "total_pages": 3,
            "has_next": True,
            "has_prev": True,
        }
        model = InvoiceListResponse.model_validate(envelope)
        # Pagination flags round-trip as Python booleans (NOT truthy strings).
        assert isinstance(model.has_next, bool)
        assert isinstance(model.has_prev, bool)
        assert model.has_next is True
        assert model.has_prev is True
        # Items went through nested InvoiceResponse coercion.
        assert isinstance(model.items, list)
        assert len(model.items) == 2
        # Both nested items have ObjectId → str coercion applied.
        assert isinstance(model.items[0].id, str)
        assert isinstance(model.items[1].id, str)
        # Pagination metadata is preserved verbatim.
        assert model.total == 50
        assert model.page == 2
        assert model.page_size == 20
        assert model.total_pages == 3

    def test_envelope_last_page_has_next_false(self):
        envelope = {
            "items": [],
            "total": 50,
            "page": 3,
            "page_size": 20,
            "has_next": False,
            "has_prev": True,
        }
        model = InvoiceListResponse.model_validate(envelope)
        assert model.has_next is False
        assert model.has_prev is True

    def test_envelope_empty_first_page(self):
        envelope = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
        }
        model = InvoiceListResponse.model_validate(envelope)
        # Defaults kick in cleanly (Pydantic v2 permissive envelope).
        assert model.has_next is False
        assert model.has_prev is False
        assert model.items == []


class TestDashboardResponseByCategoryAnyList:
    """Invariant #3: ``by_category: list[Any]`` accepts heterogeneous nested payloads.

    The dashboard's ``by_category`` aggregate is a list of dicts from MongoDB's
    ``$group`` pipeline (each ``{"category": string, "total": float, "count": int}``)
    but the model declares ``list[Any]`` to accept any future shape (mixed types,
    sentinel defaults during partial outages, etc.). The wire MUST flow the list
    through verbatim under ``extra="allow"``.
    """

    def test_by_category_accepts_mixed_types_verbatim(self):
        """Heterogeneous items survive untouched — Pydantic does NOT reformat."""
        heterogeneous = [
            {"category": "Bebidas", "total": 250.0, "count": 12},
            {"category": "Snacks", "total": 180.0, "count": 8},
            "string-sentinel-skip",  # must NOT crash
            42,                        # int sentinel (e.g. partial-outage marker)
            None,                      # None traffic on panic-restart
        ]
        doc = {
            "month_total": 430.0,
            "pending_count": 5,
            "pending_value": 50.0,
            "total_budget": 10000.0,
            "total_spent": 430.0,
            "budget_execution_pct": 4.3,
            "budget_remaining": 9570.0,
            "monthly_breakdown": [{"month": "2024-01", "total": 430.0}],
            "by_category": heterogeneous,
        }
        model = DashboardResponse.model_validate(doc)
        # by_category flowed through verbatim.
        assert isinstance(model.by_category, list)
        assert len(model.by_category) == len(heterogeneous)
        # Spot-check the heterogeneous items survive untouched.
        assert model.by_category[0]["category"] == "Bebidas"
        assert model.by_category[0]["total"] == 250.0
        assert model.by_category[1]["count"] == 8
        assert model.by_category[2] == "string-sentinel-skip"
        assert model.by_category[3] == 42
        assert model.by_category[4] is None
        # monthly_breakdown (also list[Any]) coexists with by_category.
        assert isinstance(model.monthly_breakdown, list)
        assert model.monthly_breakdown[0]["month"] == "2024-01"

    def test_by_category_defaults_to_empty_list_when_absent(self):
        """`Field(default_factory=list)` MUST serialize as [] when ``by_category`` missing."""
        doc = {
            "month_total": 0.0,
            "total_budget": 10000.0,
            "total_spent": 0.0,
        }
        model = DashboardResponse.model_validate(doc)
        assert model.by_category == []
        assert model.monthly_breakdown == []
        assert isinstance(model.by_category, list)

    def test_by_category_preserves_dict_shape_when_uniform(self):
        """Even when all items are dicts, Pydantic must NOT coerce their keys."""
        items = [
            {"category": "Bebidas", "total": 100.0, "count": 5},
            {"category": "Snacks", "total": 50.0, "count": 3},
        ]
        doc = {"by_category": items}
        model = DashboardResponse.model_validate(doc)
        assert len(model.by_category) == 2
        for item, source_item in zip(model.by_category, items):
            assert item == source_item  # dict equality (key-by-key)


class TestTrialBalanceResponseTotalsIsBalanced:
    """Invariant #4: ``totals: dict[str, Any] | None`` preserves ``is_balanced`` bool.

    The trial-balance endpoint computes ``totals = {total_debits, total_credits,
    difference, is_balanced}`` via MongoDB ``$group`` + Python float rounding;
    ``is_balanced`` MUST survive the ``model_validate`` round-trip as a Python
    ``bool`` (not int, not str, not ``None``). The ledger page frontend uses
    this flag to greenlight the balance sheet report.
    """

    def test_totals_is_balanced_bool_round_trips_true(self):
        doc = {
            "rows": [
                {"account_code": "1050", "account_name": "Caja", "account_type": "asset",
                 "normal_balance": "debit", "total_debits": 100.0, "total_credits": 0.0,
                 "balance": 100.0, "tx_count": 5, "is_zero_balance": False},
                {"account_code": "2010", "account_name": "Cuentas por pagar",
                 "account_type": "liability", "normal_balance": "credit",
                 "total_debits": 0.0, "total_credits": 100.0, "balance": -100.0,
                 "tx_count": 3, "is_zero_balance": False},
            ],
            "totals": {
                "total_debits": 100.0,
                "total_credits": 100.0,
                "difference": 0.0,
                "is_balanced": True,
            },
            "filters": {
                "prop_id": 1,
                "accounting_period": "2024-01",
            },
            "account_count": 2,
        }
        model = TrialBalanceResponse.model_validate(doc)
        # ``totals`` flowed through verbatim.
        assert isinstance(model.totals, dict)
        # ``is_balanced`` MUST be a Python ``bool``, not 1/0/None/'yes'.
        assert isinstance(model.totals["is_balanced"], bool), (
            f"is_balanced must be bool, got {type(model.totals['is_balanced']).__name__!r}"
        )
        assert model.totals["is_balanced"] is True
        # Numeric fields round-trip as floats.
        assert model.totals["total_debits"] == 100.0
        assert model.totals["total_credits"] == 100.0
        assert model.totals["difference"] == 0.0

    def test_totals_is_balanced_bool_round_trips_false(self):
        """An unbalanced ledger must surface ``is_balanced: False`` (not None)."""
        doc = {
            "rows": [],
            "totals": {
                "total_debits": 100.0,
                "total_credits": 99.5,
                "difference": 0.5,
                "is_balanced": False,
            },
            "account_count": 0,
        }
        model = TrialBalanceResponse.model_validate(doc)
        assert model.totals["is_balanced"] is False
        # Confirm static type is bool, not int (Pydantic refuses implicit cast).
        assert isinstance(model.totals["is_balanced"], bool)

    def test_totals_defaults_to_none_when_absent(self):
        """`totals: dict[str, Any] | None = None` MUST accept missing field."""
        doc = {
            "rows": [],
            "account_count": 0,
            # ``totals`` deliberately absent.
        }
        model = TrialBalanceResponse.model_validate(doc)
        assert model.totals is None

    def test_filters_dict_preserved_alongside_totals(self):
        """Cross-check: ``filters: dict[str, Any] | None`` mirrors ``totals`` semantics."""
        doc = {
            "rows": [],
            "totals": {"is_balanced": True, "total_debits": 0.0, "total_credits": 0.0, "difference": 0.0},
            "filters": {"prop_id": 1, "accounting_period": "2024-01"},
            "account_count": 0,
        }
        model = TrialBalanceResponse.model_validate(doc)
        assert isinstance(model.filters, dict)
        assert model.filters["prop_id"] == 1
        assert model.filters["accounting_period"] == "2024-01"
        # Both nested dicts coexist.
        assert model.totals["is_balanced"] is True
