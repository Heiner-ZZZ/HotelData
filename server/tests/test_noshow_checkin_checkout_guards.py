"""Guards para reservas no-show / sin check-in.

Reglas de negocio (práctica hotelera estándar — la estadía terminó y el
huésped nunca llegó):

1. Un huésped que nunca llegó y cuya estadía ya terminó (check-out pasado)
   es un NO-SHOW: no se puede hacer check-in.
2. Una reserva marcada explícitamente como ``no_show`` tampoco admite
   check-in (estado terminal de la estancia).
3. El check-out solo aplica a estancias activas (``stay_status=checked_in``):
   una reserva que nunca tuvo check-in no se puede liquidar.
4. El job automático de no-show debe detectar reservas SIN ``stay_status``
   explícito (campo ausente/vacío), no solo las ``pending`` — el bug que
   dejó colgadas reservas confirmadas sin llegar.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service._checkinout import complete_check_in, complete_check_out
from src.app.modules.reservations.service.no_show import auto_process_no_shows, process_no_show


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_booking(
    db,
    booking_id: str,
    *,
    check_in_date: str,
    check_out_date: str,
    stay_status: str | None = None,
    status: str = "confirmed",
    prop_id: int = 991,
) -> None:
    """Seed a minimal confirmed booking (no assigned rooms → light check-in)."""
    doc = {
        "booking_id": booking_id,
        "prop_id": prop_id,
        "guest_name": "No Show Guest",
        "guest_email": "noshow@test.com",
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "total_price": 218.0,
        "currency": "USD",
        "total_nights": 2,
        "rooms": 1,
        "assigned_rooms": [],
        "status": status,
        "is_test": True,
        "created_at": datetime.now(timezone.utc),
    }
    if stay_status is not None:
        doc["stay_status"] = stay_status
    db.booking_orders.insert_one(doc)


class TestCheckInNoShowGuard:
    def test_checkin_blocked_when_checkout_date_passed(self, db):
        """Estadía terminada + huésped nunca llegó → no-show → check-in bloqueado.

        El mensaje debe hablar de no-show (check-out vencido), no del error
        genérico de fecha de check-in pasada.
        """
        _seed_booking(
            db, "BK-NOSHOW-ENDED",
            check_in_date=_days_from_today(-8),
            check_out_date=_days_from_today(-1),
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-NOSHOW-ENDED", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "no-show" in message
        assert "check-out" in message

    def test_checkin_blocked_for_explicit_no_show_stay(self, db):
        """stay_status=no_show (estado terminal) bloquea el check-in."""
        _seed_booking(
            db, "BK-NOSHOW-EXPLICIT",
            check_in_date=_days_from_today(0),
            check_out_date=_days_from_today(2),
            stay_status="no_show",
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-NOSHOW-EXPLICIT", changed_by="recep.prueba")

        assert "no-show" in str(excinfo.value).lower()

    def test_checkin_still_allowed_same_day_confirmed(self, db):
        """Regresión: reserva confirmada con check-in hoy sigue siendo válida."""
        _seed_booking(
            db, "BK-OK-TODAY",
            check_in_date=_days_from_today(0),
            check_out_date=_days_from_today(2),
        )

        result = complete_check_in("BK-OK-TODAY", changed_by="recep.prueba")

        assert result["stay_status"] == "checked_in"
        doc = db.booking_orders.find_one({"booking_id": "BK-OK-TODAY"})
        assert doc["stay_status"] == "checked_in"


class TestCheckOutWithoutCheckInGuard:
    def test_checkout_blocked_when_never_checked_in(self, db):
        """Una reserva que nunca tuvo check-in no se puede liquidar."""
        _seed_booking(
            db, "BK-NO-CI",
            check_in_date=_days_from_today(-1),
            check_out_date=_days_from_today(1),
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_out("BK-NO-CI", changed_by="recep.prueba", keys_returned=True)

        message = str(excinfo.value).lower()
        assert "check-in" in message
        assert "estancia" in message or "check-out" in message

    def test_checkout_blocked_for_pending_stay(self, db):
        """stay_status=pending (sin check-in registrado) también se bloquea."""
        _seed_booking(
            db, "BK-PENDING",
            check_in_date=_days_from_today(-1),
            check_out_date=_days_from_today(1),
            stay_status="pending",
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_out("BK-PENDING", changed_by="recep.prueba", keys_returned=True)

        assert "check-in" in str(excinfo.value).lower()


class TestAutoNoShowDetectsMissingStayStatus:
    def test_auto_no_show_processes_booking_without_stay_status(self, db):
        """El job nocturno debe atrapar reservas confirmadas sin stay_status
        (campo ausente), no solo las ``pending`` explícitas."""
        _seed_booking(
            db, "BK-AUTO-MISSING",
            check_in_date=_days_from_today(-2),
            check_out_date=_days_from_today(2),
        )

        summary = auto_process_no_shows()

        assert summary["processed"] >= 1
        doc = db.booking_orders.find_one({"booking_id": "BK-AUTO-MISSING"})
        assert doc["stay_status"] == "no_show"


class TestNoShowReturnsFolio:
    def test_process_no_show_returns_folio_number_of_penalty(self, db):
        """El cierre manual de no-show debe devolver el folio de la
        penalización para que la UI de check-in lo muestre con enlace a
        Facturación (folio FL-NS-* + posting de penalización)."""
        _seed_booking(
            db, "BK-NS-FOLIO",
            check_in_date=_days_from_today(-3),
            check_out_date=_days_from_today(-1),
        )

        result = process_no_show("BK-NS-FOLIO", changed_by="recep.prueba")

        assert result["ok"] is True
        assert "folio_number" in result
        assert result["folio_number"]

        folio = db.guest_folios.find_one({"booking_id": "BK-NS-FOLIO"})
        assert folio is not None
        assert folio["folio_number"] == result["folio_number"]
        assert folio["total_due"] == result["penalty_amount"]
        assert folio["postings"][0]["reference_type"] == "no_show_penalty"
