"""Pin the wire-shape invariants of the Fase #4 billing ``*Response`` classes.

These tests interrogate the Pydantic models directly — no HTTP round-trip —
because the underlying invariant is the model itself: ``ObjectIdStr`` +
``AliasChoices`` + ``populate_by_name`` MUST turn raw Mongo ``_id``
ObjectIds into plain string ``id`` on the wire, MUST recursively coerce
nested payloads, and MUST accept permissive ``list[Any]`` payloads for
nested arrays of arbitrary shape.

If any of these assertions fails after a future refactor, the wire shape
of ``/api/billing/*`` will silently drift — the test serves as a tripwire.

Mirrors the ``TestObjectIdStrKeepInSync`` pattern in
``test_partner_history.py``.
"""
from __future__ import annotations

import pytest
from bson import ObjectId

from src.app.modules.billing.routes import (
    ActionResponse,
    FolioResponse,
    InvoiceListResponse,
    InvoiceResponse,
    PaymentResponse,
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
            "booking_id": "BK-100",
            "prop_id": 1,
            "invoice_number": "INV-001",
            "status": "issued",
            "currency": "USD",
            "subtotal": 100.0,
            "taxes": 16.0,
            "total": 116.0,
            "line_items": [],
        }
        model = InvoiceResponse.model_validate(doc)
        # ObjectIdStr BeforeValidator turned ObjectId into str.
        assert isinstance(model.id, str), (
            f"id must be str on the wire, got {type(model.id).__name__}: {model.id!r}"
        )
        # Round-trips back to the same 24-char hex.
        assert model.id == str(oid)
        assert len(model.id) == 24
        # No MongoDB-shape leakage on the wire representation.
        assert "$oid" not in model.id

    def test_string_in_underscore_id_passes_through_unchanged(self):
        """Pre-stringified ``_id`` (list-enrich path) must not double-coerce."""
        existing_str = str(ObjectId())
        doc = {
            "_id": existing_str,
            "prop_id": 1,
            "status": "issued",
            "total": 50.0,
        }
        model = InvoiceResponse.model_validate(doc)
        assert model.id == existing_str

    def test_id_field_through_alias_id_via_populate_by_name(self):
        """``populate_by_name=True`` allows construction via the wire name ``id``."""
        wire_doc = {
            "id": str(ObjectId()),
            "prop_id": 1,
            "status": "paid",
            "total": 0.0,
        }
        model = InvoiceResponse.model_validate(wire_doc)
        assert model.id == wire_doc["id"]


class TestInvoiceListResponsePaginationFlags:
    """Invariant #2: envelope returns ``has_next`` and ``has_prev`` booleans.

    Locks the pagination shape so frontend paginator components can rely
    on these keys being present even if the service layer signature drifts.
    """

    def test_envelope_carries_pagination_flags(self):
        envelope = {
            "items": [
                {
                    "_id": ObjectId(),
                    "prop_id": 1,
                    "status": "issued",
                    "total": 100.0,
                },
            ],
            "total": 25,
            "page": 2,
            "page_size": 20,
            "total_pages": 2,
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
        assert len(model.items) == 1
        assert isinstance(model.items[0].id, str)
        assert model.total == 25
        assert model.page == 2
        assert model.page_size == 20
        assert model.total_pages == 2

    def test_envelope_last_page_has_next_false(self):
        envelope = {
            "items": [],
            "total": 25,
            "page": 2,
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


class TestActionResponseNestedPaymentRecursion:
    """Invariant #3: ``payment: PaymentResponse | None`` validates recursively.

    When ``ActionResponse`` is constructed via ``model_validate`` with a
    nested ``payment`` dict containing raw ``_id: ObjectId``, the inner
    ``PaymentResponse`` MUST apply the same ObjectIdStr coercion. This is
    the regression test for ``pay_invoice_api`` and ``my_invoice_pay_api``
    endpoints, which build the payload as ``{"payment": <raw_payment_dict>}``.
    """

    def test_nested_payment_object_id_is_coerced_to_str(self):
        oid = ObjectId()
        nested_payment = {
            "_id": oid,
            "booking_id": "BK-200",
            "prop_id": 1,
            "amount": 116.0,
            "currency": "USD",
            "method": "simulated",
            "status": "captured",
            "reference": "PAY-XYZ-001",
            "created_at": "2024-01-01T12:00:00",
        }
        action = {
            "ok": True,
            "message": "Pago procesado exitosamente",
            "payment": nested_payment,
        }
        model = ActionResponse.model_validate(action)
        assert model.ok is True
        assert model.message == "Pago procesado exitosamente"
        # Recursive coercion worked: PaymentResponse was constructed (not a dict).
        assert isinstance(model.payment, PaymentResponse), (
            "Payment field must recursively bind PaymentResponse, "
            f"got {type(model.payment).__name__}"
        )
        assert isinstance(model.payment.id, str)
        assert model.payment.id == str(oid)
        assert len(model.payment.id) == 24
        # Money fields round-trip untouched.
        assert model.payment.amount == 116.0
        assert model.payment.method == "simulated"

    def test_nested_payment_missing_passes_through_as_none(self):
        """``payment: PaymentResponse | None = None`` must accept missing field."""
        action = {
            "ok": True,
            "message": "Email sent",
        }
        model = ActionResponse.model_validate(action)
        assert model.payment is None

    def test_action_response_accepts_action_with_payment_none_explicit(self):
        """Explicit ``payment: None`` is also valid."""
        action = {
            "ok": True,
            "message": "Cancelled",
            "payment": None,
        }
        model = ActionResponse.model_validate(action)
        assert model.payment is None


class TestFolioResponsePostingsAnyList:
    """Invariant #4: ``postings: list[Any]`` accepts heterogeneous nested payloads.

    ``FolioResponse.postings`` is annotated ``list[Any] = Field(default_factory=list)``
    to defer strict coercion — folio postings can be deeply nested (charges,
    discounts, payments, adjustments) with arbitrary service-side metadata.
    The wire MUST flow the array through verbatim under ``extra="allow"``,
    otherwise the frontend's posting timeline breaks on a future migration.
    """

    def test_postings_accepts_mixed_types_verbatim(self):
        heterogeneous = [
            {"posting_id": "P1", "type": "charge", "amount": 50.0},
            {"posting_id": "P2", "type": "payment", "amount": -50.0},
            "string-sentinel",  # must NOT crash
            42,                  # int sentinel
            None,                # None in a list is legal
        ]
        doc = {
            "_id": ObjectId(),
            "booking_id": "BK-300",
            "prop_id": 1,
            "folio_number": "FOL-001",
            "status": "open",
            "currency": "USD",
            "total_charges": 100.0,
            "total_payments": 50.0,
            "total_due": 50.0,
            "postings": heterogeneous,
        }
        model = FolioResponse.model_validate(doc)
        # ``postings`` flowed through verbatim — Pydantic did NOT reformat.
        assert isinstance(model.postings, list)
        assert len(model.postings) == len(heterogeneous)
        # Spot-check the heterogenous items survive untouched.
        assert model.postings[0]["posting_id"] == "P1"
        assert model.postings[1]["amount"] == -50.0
        assert model.postings[2] == "string-sentinel"
        assert model.postings[3] == 42
        assert model.postings[4] is None

    def test_postings_defaults_to_empty_list_when_absent(self):
        """`Field(default_factory=list)` MUST serialize as [] when ``postings`` missing."""
        doc = {
            "_id": ObjectId(),
            "booking_id": "BK-301",
            "prop_id": 1,
            "folio_number": "FOL-002",
            "status": "closed",
        }
        model = FolioResponse.model_validate(doc)
        assert model.postings == []
        assert isinstance(model.postings, list)

    def test_folio_response_id_coerces_object_id(self):
        """Cross-check: FolioResponse.id uses the same ObjectIdStr coercion."""
        oid = ObjectId()
        doc = {
            "_id": oid,
            "booking_id": "BK-302",
            "prop_id": 1,
            "status": "open",
        }
        model = FolioResponse.model_validate(doc)
        assert isinstance(model.id, str)
        assert model.id == str(oid)
