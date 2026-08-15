"""Check-in de llegada tardía post-medianoche.

Política del sprint: una reserva cuyo check-in fue AYER sigue siendo
checkeable como ``late_arrival`` (el huésped llegó después de la medianoche),
siempre que no sea no-show y el check-out no haya vencido. La fecha de la
reserva NO se mueve: ``check_in_date`` conserva el día reservado y
``check_in_date_actual`` registra el día real de llegada. Más de un día de
retraso = caso de no-show/gerente, no check-in normal.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service._checkinout import complete_check_in


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_booking(
    db,
    booking_id: str,
    *,
    check_in: int,
    check_out: int,
    stay_status: str | None = None,
) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 991,
        "guest_name": "Late Arrival Guest",
        "guest_email": "late@test.com",
        "status": "confirmed",
        "check_in_date": _days_from_today(check_in),
        "check_out_date": _days_from_today(check_out),
        "total_nights": 2,
        "total_price": 250.0,
        "currency": "USD",
        "assigned_rooms": [],
        "is_test": True,
    }
    if stay_status is not None:
        doc["stay_status"] = stay_status
    db.booking_orders.insert_one(doc)


class TestPostMidnightLateArrival:
    def test_yesterday_booking_checks_in_as_late_arrival(self, db) -> None:
        """Llegada después de medianoche: reserva de ayer → check-in válido."""
        _seed_booking(db, "BK-LA-CHECKIN", check_in=-1, check_out=2)

        result = complete_check_in("BK-LA-CHECKIN", changed_by="recep.prueba")

        assert result["stay_status"] == "checked_in"
        assert result["check_in_mode"] == "late_arrival"
        doc = db.booking_orders.find_one({"booking_id": "BK-LA-CHECKIN"})
        assert doc["stay_status"] == "checked_in"
        assert doc["check_in_mode"] == "late_arrival"

    def test_late_arrival_keeps_original_dates(self, db) -> None:
        """La fecha reservada no se mueve por una llegada post-medianoche."""
        check_in_date = _days_from_today(-1)
        check_out_date = _days_from_today(2)
        _seed_booking(db, "BK-LA-DATES", check_in=-1, check_out=2)

        complete_check_in("BK-LA-DATES", changed_by="recep.prueba")

        doc = db.booking_orders.find_one({"booking_id": "BK-LA-DATES"})
        assert doc["check_in_date"] == check_in_date
        assert doc["check_out_date"] == check_out_date
        assert doc["check_in_date_actual"] == local_today()

    def test_two_days_late_is_blocked_as_no_show_case(self, db) -> None:
        """2+ días de retraso = reapertura o autorización de gerente, nunca
        check-in normal."""
        _seed_booking(db, "BK-2DAYS", check_in=-2, check_out=2)

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-2DAYS", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "no-show" in message or "gerente" in message
        doc = db.booking_orders.find_one({"booking_id": "BK-2DAYS"})
        assert doc.get("stay_status") in (None, "pending")

    def test_same_day_booking_stays_normal_mode(self, db) -> None:
        """Regresión: el check-in del día reservado sigue en modo normal."""
        _seed_booking(db, "BK-NORMAL", check_in=0, check_out=2)

        result = complete_check_in("BK-NORMAL", changed_by="recep.prueba")

        assert result["check_in_mode"] == "normal"
        doc = db.booking_orders.find_one({"booking_id": "BK-NORMAL"})
        assert doc["check_in_mode"] == "normal"

    def test_late_arrival_blocked_when_stay_already_no_show(self, db) -> None:
        _seed_booking(db, "BK-NS-END", check_in=-1, check_out=2, stay_status="no_show")

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-NS-END", changed_by="recep.prueba")

        assert "no-show" in str(excinfo.value).lower()

    def test_late_arrival_blocked_when_checkout_passed(self, db) -> None:
        """Estadía terminada (check-out vencido) → no-show, no llegada tardía."""
        _seed_booking(db, "BK-ENDED", check_in=-1, check_out=-1)

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-ENDED", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "no-show" in message or "check-out" in message
