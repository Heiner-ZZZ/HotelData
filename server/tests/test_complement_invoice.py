"""Factura complementaria por el gap ("factura corta").

Cuando una factura emitida no cubre los cargos adicionales actuales (cargos
registrados después de facturar), ``create_complement_invoice`` emite una
factura de consumos por EXACTAMENTE los cargos activos que no figuran en la
factura principal. Idempotente por snapshot; inmutable tras pagos confirmados.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from tests.conftest import login

_UTC = UTC


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _booking(db, *, booking_id: str, prop_id: int = 940, total_price: float = 200.0) -> str:
    db.dim_hotels.insert_one({"prop_id": prop_id, "display_name": f"Hotel {prop_id}"})
    db.booking_orders.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "Complement Guest",
        "total_price": total_price,
        "total_nights": 2,
        "status": "confirmed",
        "stay_status": "checked_in",
        "check_in_date": "2026-08-10",
        "check_out_date": "2026-08-12",
        "created_at": datetime.now(_UTC),
    })
    return booking_id


def _charge(db, booking_id: str, *, concept: str = "Minibar", total: float = 50.0, status: str = "active") -> str:
    result = db.additional_charges.insert_one({
        "booking_id": booking_id,
        "prop_id": 940,
        "concept": concept,
        "amount": total,
        "quantity": 1,
        "total": total,
        "status": status,
        "category": "otros",
        "note": "",
        "created_at": _iso(datetime.now(_UTC)),
    })
    return str(result.inserted_id)


def _main_invoice(db, booking_id: str, *, subtotal: float = 200.0, line_charge_id: str | None = None) -> str:
    """Factura principal (la que quedó corta). ``line_charge_id`` simula un
    cargo ya plegado en la factura → no forma parte del gap."""
    line_items: list[dict] = []
    if line_charge_id:
        line_items.append({
            "type": "additional_charge",
            "charge_id": line_charge_id,
            "concept": "Facturado",
            "amount": 25.0,
            "quantity": 1,
            "total": 25.0,
        })
    result = db.reservation_invoices.insert_one({
        "booking_id": booking_id,
        "prop_id": 940,
        "invoice_number": f"INV-COMP-TEST-{booking_id}",
        "status": "issued",
        "subtotal": subtotal,
        "room_subtotal": subtotal,
        "extras_total": 0.0,
        "taxes": round(subtotal * 0.16, 2),
        "total": round(subtotal * 1.16, 2),
        "line_items": line_items,
        "issued_at": _iso(datetime.now(_UTC)),
        "paid_at": None,
    })
    return str(result.inserted_id)


def _covered_subtotal(db, booking_id: str) -> float:
    return round(sum(
        float(i.get("subtotal", 0) or 0)
        for i in db.reservation_invoices.find(
            {"booking_id": booking_id, "status": {"$ne": "cancelled"}}, {"subtotal": 1}
        )
    ), 2)


# ── Service level ─────────────────────────────────────────────────────────


def test_complement_covers_exact_gap_and_links_parent(db):
    from src.app.modules.billing.service import create_complement_invoice

    booking_id = _booking(db, booking_id="BK-COMP-GAP")
    main_id = _main_invoice(db, booking_id, subtotal=200.0)
    charge_id = _charge(db, booking_id, concept="Cena", total=50.0)

    created = create_complement_invoice(booking_id)
    assert created is not None
    assert created["subtotal"] == 50.0
    assert created["taxes"] == 8.0
    assert created["total"] == 58.0
    assert created["status"] == "issued"

    doc = db.reservation_invoices.find_one({"_id": ObjectId(created["id"])})
    assert doc["split_type"] == "charges_only"
    assert doc["complement_type"] == "gap"
    assert doc["parent_invoice_id"] == main_id
    assert [li["charge_id"] for li in doc["line_items"]] == [charge_id]

    # covered_subtotal (lo que la facturación ya cubre) = 200 principal + 50 complementaria.
    assert _covered_subtotal(db, booking_id) == 250.0

    # Trazabilidad: historia del booking con el monto del gap.
    hist = db.booking_status_history.find_one(
        {"booking_id": booking_id, "status": "complement_invoice"}
    )
    assert hist is not None
    assert "50.00" in hist["reason"]


def test_complement_is_idempotent_for_the_same_snapshot(db):
    from src.app.modules.billing.service import create_complement_invoice

    booking_id = _booking(db, booking_id="BK-COMP-IDEM")
    _main_invoice(db, booking_id)
    _charge(db, booking_id, total=30.0)

    first = create_complement_invoice(booking_id)
    second = create_complement_invoice(booking_id)
    assert first is not None and second is not None
    assert first["id"] == second["id"]
    # Solo principal + complementaria: no duplica documentos.
    assert db.reservation_invoices.count_documents({"booking_id": booking_id}) == 2


def test_complement_rebuilds_issued_projection_when_snapshot_changes(db):
    from src.app.modules.billing.service import create_complement_invoice

    booking_id = _booking(db, booking_id="BK-COMP-REBUILD")
    _main_invoice(db, booking_id, subtotal=200.0)
    charge_id = _charge(db, booking_id, total=10.0)

    first = create_complement_invoice(booking_id)
    assert first is not None and first["subtotal"] == 10.0

    # El cargo cambió antes del pago → la complementaria issued se reconstruye.
    db.additional_charges.update_one({"_id": ObjectId(charge_id)}, {"$set": {"amount": 20.0, "total": 20.0}})
    rebuilt = create_complement_invoice(booking_id)
    assert rebuilt is not None
    assert rebuilt["id"] == first["id"]
    assert rebuilt["subtotal"] == 20.0
    assert db.reservation_invoices.count_documents({"booking_id": booking_id}) == 2


def test_complement_is_immutable_after_confirmed_payment(db):
    from src.app.modules.billing.service import create_complement_invoice

    booking_id = _booking(db, booking_id="BK-COMP-PAID")
    _main_invoice(db, booking_id)
    charge_id = _charge(db, booking_id, total=10.0)

    created = create_complement_invoice(booking_id)
    assert created is not None
    db.reservation_payments.insert_one({
        "invoice_id": ObjectId(created["id"]),
        "booking_id": booking_id,
        "status": "confirmed",
        "amount": created["total"],
        "paid_at": _iso(datetime.now(_UTC)),
    })
    db.additional_charges.update_one({"_id": ObjectId(charge_id)}, {"$set": {"amount": 25.0, "total": 25.0}})

    with pytest.raises(ValueError, match="pagos confirmados"):
        create_complement_invoice(booking_id)


def test_complement_none_without_main_invoice(db):
    from src.app.modules.billing.service import create_complement_invoice

    booking_id = _booking(db, booking_id="BK-COMP-NO-MAIN")
    _charge(db, booking_id, total=10.0)

    assert create_complement_invoice(booking_id) is None


def test_complement_none_when_charges_are_already_invoiced(db):
    from src.app.modules.billing.service import create_complement_invoice

    booking_id = _booking(db, booking_id="BK-COMP-COVERED")
    charge_id = _charge(db, booking_id, total=25.0)
    _main_invoice(db, booking_id, subtotal=200.0, line_charge_id=charge_id)

    # El único cargo activo ya está plegado en la factura principal → sin gap.
    assert create_complement_invoice(booking_id) is None


def test_complement_ignores_reversed_charges(db):
    from src.app.modules.billing.service import create_complement_invoice

    booking_id = _booking(db, booking_id="BK-COMP-REVERSED")
    _main_invoice(db, booking_id)
    _charge(db, booking_id, total=10.0, status="reversed")

    assert create_complement_invoice(booking_id) is None


# ── HTTP level ────────────────────────────────────────────────────────────


def _open_shift(db, prop_id: int = 940) -> str:
    db.reception_shifts.delete_many({"prop_id": prop_id})
    result = db.reception_shifts.insert_one({
        "prop_id": prop_id,
        "status": "open",
        "shift_type": "morning",
        "employee": "Teller Complement",
        "opened_by": "admin_test",
        "start_time": _iso(datetime.now(_UTC) - timedelta(hours=1)),
        "cash_initial": 100.0,
        "total_collected": 0.0,
        "transactions": [],
    })
    return str(result.inserted_id)


@pytest.mark.asyncio
async def test_http_complement_requires_active_shift(client, admin_user, db):
    booking_id = _booking(db, booking_id="BK-COMP-HTTP-NOSHIFT")
    _main_invoice(db, booking_id)
    _charge(db, booking_id, total=50.0)

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    response = await client.post("/api/billing/invoices/complement", json={"booking_id": booking_id})

    assert response.status_code == 409
    assert "turno" in response.json()["detail"]


@pytest.mark.asyncio
async def test_http_complement_emits_with_shift(client, admin_user, db):
    booking_id = _booking(db, booking_id="BK-COMP-HTTP-OK")
    _main_invoice(db, booking_id, subtotal=200.0)
    _charge(db, booking_id, concept="Spa", total=50.0)
    _open_shift(db)

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    response = await client.post("/api/billing/invoices/complement", json={"booking_id": booking_id})

    assert response.status_code == 201
    data = response.json()
    assert data["subtotal"] == 50.0
    assert data["taxes"] == 8.0
    assert data["total"] == 58.0
    assert data["status"] == "issued"

    doc = db.reservation_invoices.find_one({"_id": ObjectId(data["id"])})
    assert doc["split_type"] == "charges_only"
    assert doc["complement_type"] == "gap"
    assert _covered_subtotal(db, booking_id) == 250.0


@pytest.mark.asyncio
async def test_http_complement_400_when_no_gap(client, admin_user, db):
    booking_id = _booking(db, booking_id="BK-COMP-HTTP-NOGAP")
    _main_invoice(db, booking_id, subtotal=200.0)
    _open_shift(db)

    assert await login(client, admin_user["username"], admin_user["password"]) == 200
    response = await client.post("/api/billing/invoices/complement", json={"booking_id": booking_id})

    assert response.status_code == 400
    assert "sin facturar" in response.json()["detail"]
