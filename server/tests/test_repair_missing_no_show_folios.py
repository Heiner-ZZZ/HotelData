#!/usr/bin/env python3
"""Pruebas de la reparación administrativa de folios no-show faltantes.

El repair debe ser seguro por defecto: el dry-run identifica únicamente
reservas con ``stay_status=no_show`` sin folio y no escribe documentos.
"""
from __future__ import annotations

from datetime import datetime, timezone

from scripts.repair_missing_no_show_folios import repair_missing_no_show_folios


def _seed_no_show(db, booking_id: str, **overrides) -> None:
    booking = {
        "booking_id": booking_id,
        "prop_id": 1,
        "guest_name": "Historical No Show",
        "guest_email": "historical@example.com",
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-03",
        "total_nights": 2,
        "currency": "USD",
        "status": "confirmed",
        "stay_status": "no_show",
        "no_show_penalty_amount": 75.0,
        "no_show_penalty_percent": 100,
        "is_test": True,
        "created_at": datetime.now(timezone.utc),
    }
    booking.update(overrides)
    db.booking_orders.insert_one(booking)


def test_dry_run_reports_missing_folio_without_writing(db):
    """El dry-run detecta el candidato y no crea folio ni auditoría."""
    _seed_no_show(db, "BK-REPAIR-0001")

    report = repair_missing_no_show_folios(db, dry_run=True)

    assert report["scanned"] == 1
    assert report["candidates"] == 1
    assert report["repaired"] == 0
    assert report["rows"] == [
        {
            "booking_id": "BK-REPAIR-0001",
            "prop_id": 1,
            "action": "would_repair",
            "folio_number": None,
            "penalty_amount": 75.0,
        }
    ]
    assert db.guest_folios.count_documents({}) == 0
    assert db.audit_log.count_documents({}) == 0


def test_apply_reconstructs_folio_and_is_idempotent(db):
    """Aplicar crea un folio auditable y repetir no duplica nada."""
    _seed_no_show(db, "BK-REPAIR-0002")

    first = repair_missing_no_show_folios(db, dry_run=False)

    assert first["candidates"] == 1
    assert first["repaired"] == 1
    assert first["rows"][0]["action"] == "repaired"
    assert first["rows"][0]["folio_number"] == "FL-NS-BK-REPAIR-0002"
    folio = db.guest_folios.find_one({"booking_id": "BK-REPAIR-0002"})
    assert folio["total_due"] == 75.0
    assert folio["repair_metadata"]["repair_id"] == "repair_missing_no_show_folios_v1"
    assert db.audit_log.count_documents({"entity_id": "BK-REPAIR-0002"}) == 1

    second = repair_missing_no_show_folios(db, dry_run=False)

    assert second["scanned"] == 1
    assert second["candidates"] == 0
    assert second["repaired"] == 0
    assert second["already_present"] == 1
    assert db.guest_folios.count_documents({"booking_id": "BK-REPAIR-0002"}) == 1
    assert db.audit_log.count_documents({"entity_id": "BK-REPAIR-0002"}) == 1



def test_filters_and_existing_folios_are_reported_without_cross_hotel_changes(db):
    """Los filtros limitan el alcance y un folio existente no se reconstruye."""
    _seed_no_show(db, "BK-REPAIR-0003", prop_id=2, check_in_date="2026-07-01")
    _seed_no_show(db, "BK-REPAIR-0004", prop_id=1, check_in_date="2026-08-05")
    db.guest_folios.insert_one({
        "booking_id": "BK-REPAIR-0004",
        "folio_number": "FL-EXISTING-0004",
        "prop_id": 1,
    })

    report = repair_missing_no_show_folios(
        db,
        dry_run=True,
        prop_id=1,
        check_in_from="2026-08-01",
        check_in_to="2026-08-31",
    )

    assert report["scanned"] == 1
    assert report["candidates"] == 0
    assert report["already_present"] == 1
    assert report["rows"] == []
    assert db.guest_folios.count_documents({"booking_id": "BK-REPAIR-0003"}) == 0



def test_limit_is_applied_after_stable_booking_sort(db):
    """El límite produce un alcance reproducible por booking_id."""
    _seed_no_show(db, "BK-REPAIR-0005")
    _seed_no_show(db, "BK-REPAIR-0006")

    report = repair_missing_no_show_folios(db, dry_run=True, limit=1)

    assert report["scanned"] == 1
    assert report["rows"][0]["booking_id"] == "BK-REPAIR-0005"



def test_non_no_show_booking_is_never_a_candidate(db):
    """Una reserva confirmada sin folio no entra en esta reparación."""
    _seed_no_show(db, "BK-REPAIR-0007", stay_status="pending")

    report = repair_missing_no_show_folios(db, dry_run=True)

    assert report["scanned"] == 0
    assert report["candidates"] == 0
    assert report["rows"] == []



def test_missing_penalty_amount_is_reported_as_skipped(db):
    """No se inventa una deuda cuando el no-show legacy no conservó importe."""
    _seed_no_show(db, "BK-REPAIR-0008", no_show_penalty_amount=None)

    report = repair_missing_no_show_folios(db, dry_run=True)

    assert report["candidates"] == 0
    assert report["skipped"] == 1
    assert report["rows"][0]["action"] == "skipped_missing_penalty"
    assert db.guest_folios.count_documents({}) == 0
