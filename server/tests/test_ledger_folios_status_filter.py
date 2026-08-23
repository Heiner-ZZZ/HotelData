"""El chip "Cerrados" de la pestaña Folios muestra todos los folios no abiertos.

Contrato: ``GET /expenses/ledger/folios?status=closed,settled,written_off``
devuelve exactamente los folios en esos tres estados (excluye ``open``), y los
filtros ``open`` / default siguen devolviendo solo folios abiertos.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.app.modules.expenses.routes import list_active_folios


def _seed_folio(db, booking_id: str, status: str, prop_id: int = 1) -> None:
    db.guest_folios.insert_one({
        "booking_id": booking_id,
        "prop_id": prop_id,
        "folio_number": f"FL-{status.upper()}-{booking_id}",
        "status": status,
        "total_room": 100.0,
        "total_charges": 100.0,
        "total_discounts": 0.0,
        "total_payments": 0.0 if status == "open" else 100.0,
        "total_due": 100.0 if status == "open" else 0.0,
        "postings": [],
        "posting_count": 0,
        "created_at": datetime.now(timezone.utc),
    })


def test_closed_bucket_returns_all_non_open_statuses(db):
    for s in ("open", "closed", "settled", "written_off"):
        _seed_folio(db, f"BK-{s}", s)

    result = list_active_folios(prop_id=1, status="closed,settled,written_off")

    assert result.total == 3
    assert {f.status for f in result.items} == {"closed", "settled", "written_off"}


def test_open_status_still_returns_only_open(db):
    for s in ("open", "closed"):
        _seed_folio(db, f"BK-{s}", s)

    result = list_active_folios(prop_id=1, status="open")

    assert result.total == 1
    assert result.items[0].status == "open"


def test_default_status_returns_only_open(db):
    for s in ("open", "closed", "settled"):
        _seed_folio(db, f"BK-{s}", s)

    result = list_active_folios(prop_id=1)

    assert result.total == 1
    assert result.items[0].status == "open"
