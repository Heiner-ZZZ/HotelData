"""Check-out detail must expose the responsible shift + cashier.

The check-out is a front-desk cash operation: the completing user's active
shift is stamped on the booking (``shift_id`` FK + ``check_out_by``). The
liquidation page needs that attribution — which shift handled the check-out
and which employee/opener is responsible — next to the guest/stay data.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from tests.conftest import login

_UTC = timezone.utc


def _seed_shift(db, prop_id: int = 1) -> str:
    result = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "employee": "Carlos Pérez",
            "opened_by": "recep.prueba",
            "start_time": datetime.now(_UTC).isoformat(),
            "cash_initial": 100.0,
            "total_collected": 0.0,
            "transactions": [],
        }
    )
    return str(result.inserted_id)


def _seed_booking(db, booking_id: str, *, shift_id: str | None) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Guest Checkout Shift",
        "guest_email": "guest@test.com",
        "cedula": "12345678",
        "check_in_date": "2026-08-09",
        "check_out_date": "2026-08-11",
        "total_price": 218.0,
        "currency": "USD",
        "total_nights": 2,
        "rooms": 1,
        "status": "confirmed",
        "stay_status": "checked_out",
        "check_out_by": "recep.prueba",
        "check_out_date_actual": "2026-08-11",
        "check_out_time_actual": "12:04",
        "assigned_rooms": [],
        "created_at": datetime.now(_UTC),
    }
    if shift_id:
        doc["shift_id"] = ObjectId(shift_id)
    db.booking_orders.insert_one(doc)


@pytest.mark.asyncio
async def test_check_out_detail_exposes_shift_and_cashier(client, db, admin_user):
    await login(client, admin_user["username"], admin_user["password"])
    shift_id = _seed_shift(db)
    _seed_booking(db, "BK-CO-SHIFT", shift_id=shift_id)

    resp = await client.get("/api/management/check-outs/BK-CO-SHIFT/detail?prop_id=1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["check_out_shift_id"] == shift_id
    shift = body["check_out_shift"]
    assert shift is not None
    assert shift["employee"] == "Carlos Pérez"
    assert shift["opened_by"] == "recep.prueba"
    assert shift["shift_type"] == "morning"
    assert shift["shift_label"]  # e.g. "Matutino (08:00-16:00)"
    assert shift["start_time"]


@pytest.mark.asyncio
async def test_check_out_detail_read_logs_shift_attribution_access(client, db, admin_user):
    """Consultar el detalle de check-out con atribución de turno deja una
    traza de acceso a datos sensibles en audit_log (quién/cuándo/qué turno)."""
    await login(client, admin_user["username"], admin_user["password"])
    shift_id = _seed_shift(db)
    _seed_booking(db, "BK-CO-TRACE", shift_id=shift_id)

    resp = await client.get("/api/management/check-outs/BK-CO-TRACE/detail?prop_id=1")

    assert resp.status_code == 200
    entry = db.audit_log.find_one(
        {"entity_type": "shift_attribution_access", "entity_id": "BK-CO-TRACE"}
    )
    assert entry is not None
    assert entry["changed_by"] == "admin_test"
    assert entry["action"] == "read"
    assert entry["metadata"]["source"] == "check_out"
    assert entry["metadata"]["shift_id"] == shift_id
    assert entry["metadata"]["shift_employee"] == "Carlos Pérez"
    assert entry["metadata"]["shift_opened_by"] == "recep.prueba"
    assert entry["metadata"]["shift_type"] == "morning"
    assert entry["metadata"]["shift_start_time"]


@pytest.mark.asyncio
async def test_check_out_detail_without_shift_logs_no_access_trace(client, db, admin_user):
    """Sin atribución de turno no hay traza de acceso sensible."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-CO-NOTRACE", shift_id=None)

    resp = await client.get("/api/management/check-outs/BK-CO-NOTRACE/detail?prop_id=1")

    assert resp.status_code == 200
    assert (
        db.audit_log.count_documents(
            {"entity_type": "shift_attribution_access", "entity_id": "BK-CO-NOTRACE"}
        )
        == 0
    )


@pytest.mark.asyncio
async def test_check_out_detail_without_shift_stays_null(client, db, admin_user):
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-CO-NOSHIFT", shift_id=None)

    resp = await client.get("/api/management/check-outs/BK-CO-NOSHIFT/detail?prop_id=1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["check_out_shift_id"] is None
    assert body["check_out_shift"] is None
