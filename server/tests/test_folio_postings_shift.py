"""Folio postings must expose the responsible shift + cashier.

``post_to_folio`` stamps ``shift_id``/``shift_employee``/``shift_opened_by``/
``shift_type`` on every posting entry (money operations are attributable to a
shift). The wire contract for ``GET /api/expenses/ledger/folios/{id}/postings``
must pass those fields through so the folio UI can show who handled each
charge/payment — the same attribution the payments list already exposes.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from tests.conftest import login


def _seed_folio(db, booking_id: str = "BK-FOLIO-SHIFT") -> str:
    shift_id = ObjectId()
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Shift Folio Guest",
        "total_price": 120.0,
        "total_nights": 1,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc),
    })
    folio_id = db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": 1,
        "folio_number": f"FL-SHIFT-{booking_id}",
        "status": "open",
        "total_room": 120.0,
        "total_charges": 120.0,
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
                "posted_at": datetime.now(timezone.utc),
            },
            {
                "posting_id": ObjectId(),
                "type": "payment",
                "category": "Pago",
                "concept": "Pago adelantado",
                "amount": 50.0,
                "quantity": 1,
                "unit_price": 50.0,
                "reference_id": "PAY-1",
                "reference_type": "payment",
                "posted_at": datetime.now(timezone.utc),
                "shift_id": shift_id,
                "shift_employee": "Carlos Pérez",
                "shift_opened_by": "gerente1",
                "shift_type": "morning",
            },
        ],
        "posting_count": 2,
    })
    return str(folio_id.inserted_id)


@pytest.mark.asyncio
async def test_folio_postings_expose_shift_and_employee(client, db, admin_user):
    await login(client, admin_user["username"], admin_user["password"])
    folio_id = _seed_folio(db)

    resp = await client.get(f"/api/expenses/ledger/folios/{folio_id}/postings?prop_id=1")

    assert resp.status_code == 200
    body = resp.json()
    by_ref = {p["reference_id"]: p for p in body["postings"]}
    payment = by_ref["PAY-1"]
    assert payment["shift_id"]
    assert payment["shift_employee"] == "Carlos Pérez"
    assert payment["shift_opened_by"] == "gerente1"
    assert payment["shift_type"] == "morning"


@pytest.mark.asyncio
async def test_folio_postings_without_shift_stay_clean(client, db, admin_user):
    await login(client, admin_user["username"], admin_user["password"])
    folio_id = _seed_folio(db)

    resp = await client.get(f"/api/expenses/ledger/folios/{folio_id}/postings?prop_id=1")

    assert resp.status_code == 200
    body = resp.json()
    room = next(p for p in body["postings"] if p["reference_id"] == "room-1")
    # Postings without attribution must not leak null shift fields.
    assert "shift_id" not in room
    assert "shift_employee" not in room
