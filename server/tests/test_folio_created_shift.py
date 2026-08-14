"""The billing folio must expose the shift that opened it (created_shift).

``create_folio`` ties the folio to the active cash shift at check-in
(``shift_id`` FK). The folio detail + its printed/PDF view need that
attribution — which shift opened the account and which cashier/opener is
responsible — alongside the postings' own shift stamps.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from tests.conftest import login

_UTC = timezone.utc


def _seed_shift(db) -> str:
    result = db.reception_shifts.insert_one(
        {
            "prop_id": 1,
            "status": "closed",
            "shift_type": "morning",
            "employee": "Ana Recepción",
            "opened_by": "recep.prueba",
            "start_time": datetime.now(_UTC).isoformat(),
            "cash_initial": 100.0,
            "total_collected": 0.0,
            "transactions": [],
        }
    )
    return str(result.inserted_id)


def _seed_booking(db, booking_id: str) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 1,
            "guest_name": "Folio Shift Guest",
            "total_price": 120.0,
            "total_nights": 1,
            "status": "confirmed",
            "created_at": datetime.now(_UTC),
        }
    )


def _seed_folio(db, booking_id: str, *, shift_id: str | None) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": f"FL-CREATED-SHIFT-{booking_id}",
        "status": "open",
        "total_room": 120.0,
        "total_charges": 0.0,
        "total_discounts": 0.0,
        "total_payments": 0.0,
        "total_due": 120.0,
        "postings": [
            {
                "posting_id": ObjectId(),
                "type": "room",
                "category": "Habitación",
                "concept": "Habitación Standard",
                "amount": 120.0,
                "quantity": 1,
                "unit_price": 120.0,
                "reference_id": "room-1",
                "reference_type": "room",
                "posted_at": datetime.now(_UTC),
            }
        ],
        "posting_count": 1,
        "created_at": datetime.now(_UTC),
        "closed_at": None,
        "closed_by": None,
        "invoice_id": None,
    }
    if shift_id:
        doc["shift_id"] = ObjectId(shift_id)
    db.guest_folios.insert_one(doc)


@pytest.mark.asyncio
async def test_folio_exposes_created_shift(client, db, admin_user):
    await login(client, admin_user["username"], admin_user["password"])
    shift_id = _seed_shift(db)
    _seed_booking(db, "BK-FOLIO-CREATED")
    _seed_folio(db, "BK-FOLIO-CREATED", shift_id=shift_id)

    resp = await client.get("/api/billing/folios/BK-FOLIO-CREATED")

    assert resp.status_code == 200
    body = resp.json()
    created = body["created_shift"]
    assert created is not None
    assert created["employee"] == "Ana Recepción"
    assert created["opened_by"] == "recep.prueba"
    assert created["shift_type"] == "morning"
    assert created["shift_label"]  # e.g. "Matutino (08:00-16:00)"
    assert created["start_time"]


@pytest.mark.asyncio
async def test_folio_read_logs_shift_attribution_access(client, db, admin_user):
    """Consultar el folio con turno (created_shift) deja una traza de acceso
    a datos sensibles en audit_log (quién/cuándo/qué turno)."""
    await login(client, admin_user["username"], admin_user["password"])
    shift_id = _seed_shift(db)
    _seed_booking(db, "BK-FOLIO-TRACE")
    _seed_folio(db, "BK-FOLIO-TRACE", shift_id=shift_id)

    resp = await client.get("/api/billing/folios/BK-FOLIO-TRACE")

    assert resp.status_code == 200
    entry = db.audit_log.find_one(
        {"entity_type": "shift_attribution_access", "entity_id": "BK-FOLIO-TRACE"}
    )
    assert entry is not None
    assert entry["changed_by"] == "admin_test"
    assert entry["action"] == "read"
    assert entry["metadata"]["source"] == "folio"
    assert entry["metadata"]["shift_id"] == shift_id
    assert entry["metadata"]["shift_employee"] == "Ana Recepción"
    assert entry["metadata"]["shift_opened_by"] == "recep.prueba"
    assert entry["metadata"]["shift_type"] == "morning"


@pytest.mark.asyncio
async def test_folio_without_shift_logs_no_access_trace(client, db, admin_user):
    """Sin turno en el folio no hay traza de acceso sensible."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-FOLIO-NOTRACE")
    _seed_folio(db, "BK-FOLIO-NOTRACE", shift_id=None)

    resp = await client.get("/api/billing/folios/BK-FOLIO-NOTRACE")

    assert resp.status_code == 200
    assert (
        db.audit_log.count_documents(
            {"entity_type": "shift_attribution_access", "entity_id": "BK-FOLIO-NOTRACE"}
        )
        == 0
    )


@pytest.mark.asyncio
async def test_folio_without_shift_stays_null(client, db, admin_user):
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-FOLIO-NOSHIFT")
    _seed_folio(db, "BK-FOLIO-NOSHIFT", shift_id=None)

    resp = await client.get("/api/billing/folios/BK-FOLIO-NOSHIFT")

    assert resp.status_code == 200
    body = resp.json()
    assert body["created_shift"] is None
