"""TDD contract for same-day early check-in.

The reservation dates remain the commercial stay dates. An early arrival is
an explicit operational mode recorded on the booking; it never shifts the
reservation or recalculates its nights.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import src.app.modules.reservations.service._checkinout._checkin as checkin_module
from src.app.modules.reservations.service import complete_check_in

FIXED_DATE = "2026-08-14"


def _seed_policy(db, *, check_in_time: str = "15:00", courtesy_minutes: int = 60) -> None:
    db.hotel_policies.insert_one(
        {
            "prop_id": 991,
            "room_type_id": "",
            "rate_plan_id": "",
            "season_id": "",
            "check_in_time": check_in_time,
            "check_out_time": "12:00",
            "early_check_in_enabled": True,
            "early_check_in_courtesy_minutes": courtesy_minutes,
            "early_check_in_default_fee": 0.0,
        }
    )


def _seed_booking(db, booking_id: str, *, assigned_rooms: list[str] | None = None) -> None:
    rooms = assigned_rooms if assigned_rooms is not None else ["ROOM-991-1"]
    if rooms:
        db.hotel_rooms.insert_one({"hotel_room_id": rooms[0], "room_label": "101", "floor": "1"})
        db.room_status_log.insert_one({"prop_id": 991, "room_label": "101", "status": "vacant_clean"})
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 991,
            "guest_name": "Early Guest",
            "guest_email": "early@test.com",
            "check_in_date": FIXED_DATE,
            "check_out_date": "2026-08-16",
            "total_price": 218.0,
            "currency": "USD",
            "total_nights": 2,
            "rooms": 1,
            "assigned_rooms": rooms,
            "status": "confirmed",
            "is_test": True,
        }
    )


def _freeze_clock(monkeypatch, *, hour: int, minute: int) -> None:
    frozen = datetime(2026, 8, 14, hour, minute, tzinfo=ZoneInfo("America/Lima"))
    monkeypatch.setattr(checkin_module, "local_today", lambda: FIXED_DATE)
    monkeypatch.setattr(checkin_module, "local_now", lambda: frozen, raising=False)


def _seed_open_shift(db, *, prop_id: int = 991) -> str:
    """Turno abierto para que ``register_transaction`` registre el check-in."""
    result = db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "employee": "Carlos Pérez",
            "opened_by": "recep.prueba",
            "start_time": datetime.now(UTC).isoformat(),
            "cash_initial": 100.0,
            "total_collected": 0.0,
            "transactions": [],
        }
    )
    return str(result.inserted_id)


class TestEarlyCheckInPolicy:
    def test_same_day_before_schedule_requires_an_explicit_mode(self, db, monkeypatch):
        """A normal check-in must not accidentally bypass the early window."""
        _seed_policy(db)
        _seed_booking(db, "BK-EARLY-EXPLICIT")
        _freeze_clock(monkeypatch, hour=14, minute=30)

        with pytest.raises(ValueError, match="early check-in"):
            complete_check_in("BK-EARLY-EXPLICIT", changed_by="recep.prueba")

        booking = db.booking_orders.find_one({"booking_id": "BK-EARLY-EXPLICIT"})
        assert booking.get("stay_status") is None
        assert booking.get("check_in_mode") is None

    def test_within_courtesy_window_records_early_courtesy_without_moving_dates(self, db, monkeypatch):
        """A 30-minute courtesy arrival keeps the original stay dates."""
        _seed_policy(db, courtesy_minutes=60)
        _seed_booking(db, "BK-EARLY-COURTESY")
        _freeze_clock(monkeypatch, hour=14, minute=30)

        result = complete_check_in(
            "BK-EARLY-COURTESY",
            changed_by="recep.prueba",
            early_check_in_mode="early_courtesy",
            early_check_in_approved=True,
        )

        assert result["stay_status"] == "checked_in"
        assert result["early_check_in_mode"] == "early_courtesy"
        booking = db.booking_orders.find_one({"booking_id": "BK-EARLY-COURTESY"})
        assert booking["check_in_date"] == FIXED_DATE
        assert booking["check_out_date"] == "2026-08-16"
        assert booking["check_in_mode"] == "early_courtesy"
        assert booking["early_check_in_minutes"] == 30
        assert booking["early_check_in_fee"] == 0.0

    def test_early_policy_and_actual_stamp_share_one_local_clock_snapshot(self, db, monkeypatch):
        """La decisión early y ``check_in_time_actual`` deben usar el mismo
        instante local: si el reloj cruza de minuto entre ambas lecturas, la
        política no puede decir 30 min mientras el sello diga 14:31."""
        _seed_policy(db, courtesy_minutes=60)
        _seed_booking(db, "BK-EARLY-CLOCK-SNAPSHOT")
        local_times = iter([
            datetime(2026, 8, 14, 14, 30, tzinfo=ZoneInfo("America/Lima")),
            datetime(2026, 8, 14, 14, 31, tzinfo=ZoneInfo("America/Lima")),
        ])
        monkeypatch.setattr(checkin_module, "local_today", lambda: FIXED_DATE)
        monkeypatch.setattr(checkin_module, "local_now", lambda: next(local_times), raising=False)

        complete_check_in(
            "BK-EARLY-CLOCK-SNAPSHOT",
            changed_by="recep.prueba",
            early_check_in_mode="early_courtesy",
            early_check_in_approved=True,
        )

        booking = db.booking_orders.find_one({"booking_id": "BK-EARLY-CLOCK-SNAPSHOT"})
        assert booking["early_check_in_minutes"] == 30
        assert booking["check_in_date_actual"] == FIXED_DATE
        assert booking["check_in_time_actual"] == "14:30"

    def test_normal_check_in_stamps_local_actual_arrival(self, db, monkeypatch):
        _seed_policy(db)
        _seed_booking(db, "BK-NORMAL-LOCAL-CLOCK")
        _freeze_clock(monkeypatch, hour=15, minute=0)

        complete_check_in("BK-NORMAL-LOCAL-CLOCK", changed_by="recep.prueba")

        booking = db.booking_orders.find_one({"booking_id": "BK-NORMAL-LOCAL-CLOCK"})
        assert booking["check_in_mode"] == "normal"
        assert booking["check_in_date_actual"] == FIXED_DATE
        assert booking["check_in_time_actual"] == "15:00"

    def test_late_arrival_check_in_stamps_local_actual_arrival(self, db, monkeypatch):
        _seed_policy(db)
        _seed_booking(db, "BK-LATE-LOCAL-CLOCK")
        db.booking_orders.update_one(
            {"booking_id": "BK-LATE-LOCAL-CLOCK"},
            {"$set": {"check_in_date": "2026-08-13", "check_out_date": "2026-08-16"}},
        )
        _freeze_clock(monkeypatch, hour=1, minute=45)

        complete_check_in("BK-LATE-LOCAL-CLOCK", changed_by="recep.prueba")

        booking = db.booking_orders.find_one({"booking_id": "BK-LATE-LOCAL-CLOCK"})
        assert booking["check_in_mode"] == "late_arrival"
        assert booking["check_in_date_actual"] == FIXED_DATE
        assert booking["check_in_time_actual"] == "01:45"

    def test_more_than_courtesy_requires_manager_approval_and_reason(self, db, monkeypatch):
        """A two-hour early arrival needs an explicit approval payload."""
        _seed_policy(db, courtesy_minutes=60)
        _seed_booking(db, "BK-EARLY-APPROVAL")
        _freeze_clock(monkeypatch, hour=13, minute=0)

        with pytest.raises(ValueError, match="aprobación"):
            complete_check_in(
                "BK-EARLY-APPROVAL",
                changed_by="recep.prueba",
                early_check_in_mode="early_courtesy",
                early_check_in_approved=True,
            )

        result = complete_check_in(
            "BK-EARLY-APPROVAL",
            changed_by="gerente.prueba",
            early_check_in_mode="early_approved",
            early_check_in_approved=True,
            early_check_in_reason="Habitación lista y gerente autorizó la entrega",
            early_check_in_fee=25.0,
            early_check_in_authorized=True,
        )

        assert result["stay_status"] == "checked_in"
        assert result["early_check_in_mode"] == "early_approved"
        assert result["early_check_in_fee"] == 25.0
        booking = db.booking_orders.find_one({"booking_id": "BK-EARLY-APPROVAL"})
        assert booking["check_in_date"] == FIXED_DATE
        assert booking["check_out_date"] == "2026-08-16"
        assert booking["early_check_in_approved_by"] == "gerente.prueba"
        assert booking["early_check_in_reason"] == "Habitación lista y gerente autorizó la entrega"

    def test_early_check_in_requires_an_assigned_available_room(self, db, monkeypatch):
        """Explicit early arrival cannot bypass the availability gate."""
        _seed_policy(db)
        _seed_booking(db, "BK-EARLY-NO-ROOM", assigned_rooms=[])
        _freeze_clock(monkeypatch, hour=14, minute=30)

        with pytest.raises(ValueError, match="disponible"):
            complete_check_in(
                "BK-EARLY-NO-ROOM",
                changed_by="gerente.prueba",
                early_check_in_mode="early_courtesy",
                early_check_in_approved=True,
            )

    def test_future_date_guard_still_wins_over_early_mode(self, db, monkeypatch):
        """Early authorization cannot turn a future-calendar booking into today."""
        _seed_policy(db)
        _seed_booking(db, "BK-EARLY-FUTURE")
        db.booking_orders.update_one(
            {"booking_id": "BK-EARLY-FUTURE"},
            {"$set": {"check_in_date": (datetime.fromisoformat(FIXED_DATE) + timedelta(days=1)).date().isoformat()}},
        )
        _freeze_clock(monkeypatch, hour=14, minute=30)

        with pytest.raises(ValueError, match="futura"):
            complete_check_in(
                "BK-EARLY-FUTURE",
                changed_by="gerente.prueba",
                early_check_in_mode="early_approved",
                early_check_in_approved=True,
                early_check_in_reason="Autorización excepcional",
            )


class TestEarlyCheckInTeamNotification:
    """El equipo (recepción/housekeeping) debe saber que la llegada anticipada
    ocupó la habitación antes de la hora de política, en ambos modos:

    - ``early_approved`` → ``notification_type: early_checkin_approved`` (con
      cargo aprobado y motivo).
    - ``early_courtesy`` → ``notification_type: early_checkin_courtesy`` (sin
      cargo, dentro de la cortesía) — la limpieza debe ajustarse igual aunque
      no haya fee.

    Mismo criterio que la notificación de late check-out en cortesía.
    """

    def test_approved_early_checkin_notifies_team_with_real_time(self, db, monkeypatch):
        """``early_approved`` registra en ``notification_log`` la llegada
        anticipada con la hora real y el cargo aprobado."""
        _seed_policy(db, courtesy_minutes=60)
        _seed_booking(db, "BK-EARLY-NOTIFY", assigned_rooms=["ROOM-991-1"])
        db.booking_orders.update_one(
            {"booking_id": "BK-EARLY-NOTIFY"},
            {"$set": {"is_test": False}},
        )
        _freeze_clock(monkeypatch, hour=13, minute=0)  # 120 min antes de las 15:00

        complete_check_in(
            "BK-EARLY-NOTIFY",
            changed_by="gerente.prueba",
            early_check_in_mode="early_approved",
            early_check_in_approved=True,
            early_check_in_reason="Gerencia autorizó entrega anticipada",
            early_check_in_fee=25.0,
            early_check_in_authorized=True,
        )

        entry = db.notification_log.find_one(
            {"entity_id": "BK-EARLY-NOTIFY", "notification_type": "early_checkin_approved"}
        )
        assert entry is not None
        message = entry["message"]
        # Hora REAL de la llegada (reloj local congelado).
        assert "13:00" in message
        assert "120 min" in message
        assert "Gerencia autorizó entrega anticipada" in message
        assert "25.00" in message
        # La traza early es propia: no hereda campos del late check-out.
        assert "late_checkout_mode" not in entry["metadata"]
        assert "late_checkout_fee" not in entry["metadata"]
        assert entry["metadata"]["early_checkin_mode"] == "early_approved"
        assert entry["metadata"]["minutes_before"] == 120
        assert entry["metadata"]["policy_check_in_time"] == "15:00"
        assert entry["metadata"]["actual_check_in_time"] == "13:00"
        assert round(float(entry["metadata"]["early_checkin_fee"]), 2) == 25.0

    def test_courtesy_early_checkin_notifies_team_without_fee(self, db, monkeypatch):
        """``early_courtesy`` también notifica: la habitación se ocupó antes de
        la hora de política sin cargo, y la limpieza debe ajustarse igual.

        Entrada ``early_checkin_courtesy`` con la hora real, sin línea de cargo
        y metadata con el modo (traza distinta de la aprobada).
        """
        _seed_policy(db, courtesy_minutes=60)
        _seed_booking(db, "BK-EARLY-COURTESY-NOTIFY", assigned_rooms=["ROOM-991-1"])
        db.booking_orders.update_one(
            {"booking_id": "BK-EARLY-COURTESY-NOTIFY"},
            {"$set": {"is_test": False}},
        )
        _freeze_clock(monkeypatch, hour=14, minute=30)  # 30 min antes de las 15:00, dentro de cortesía

        complete_check_in(
            "BK-EARLY-COURTESY-NOTIFY",
            changed_by="recep.prueba",
            early_check_in_mode="early_courtesy",
            early_check_in_approved=True,
        )

        entry = db.notification_log.find_one(
            {"entity_id": "BK-EARLY-COURTESY-NOTIFY", "notification_type": "early_checkin_courtesy"}
        )
        assert entry is not None
        message = entry["message"]
        # Hora REAL de la llegada (reloj local congelado).
        assert "14:30" in message
        assert "30 min" in message
        # Sin cargo: el mensaje lo dice y no hay línea de cargo.
        assert "cortesía" in message
        assert "Cargo:" not in message
        assert entry["metadata"]["early_checkin_mode"] == "early_courtesy"
        assert entry["metadata"]["minutes_before"] == 30
        assert entry["metadata"]["policy_check_in_time"] == "15:00"
        assert entry["metadata"]["actual_check_in_time"] == "14:30"
        assert round(float(entry["metadata"]["early_checkin_fee"]), 2) == 0.0


class TestEarlyFeeEntersShift:
    """El fee early posteado al folio debe entrar al turno (conciliación).

    ``register_transaction`` del check-in re-lee el folio DESPUÉS de crear el
    folio y postear el early fee: el fetch del booking al inicio del flujo no
    conoce el folio (aún no existía) y si el txn del turno quedara en $0, el
    reporte de turno sub-colectaría el early check-in.
    """

    def test_early_fee_reconciles_in_folio_and_shift(self, db, monkeypatch):
        """Conciliación: shift.amount == folio.total_due (habitación + fee early)."""
        _seed_policy(db, check_in_time="15:00", courtesy_minutes=60)
        _seed_booking(db, "BK-EARLY-SHIFT", assigned_rooms=["ROOM-991-1"])
        db.booking_orders.update_one(
            {"booking_id": "BK-EARLY-SHIFT"},
            {"$set": {"is_test": False}},
        )
        _seed_open_shift(db)
        _freeze_clock(monkeypatch, hour=13, minute=0)  # 120 min antes de las 15:00

        complete_check_in(
            "BK-EARLY-SHIFT",
            changed_by="gerente.prueba",
            early_check_in_mode="early_approved",
            early_check_in_approved=True,
            early_check_in_reason="Gerencia autorizó entrega anticipada",
            early_check_in_fee=25.0,
            early_check_in_authorized=True,
        )

        # Fee early posteado al folio (habitación 218 + fee 25 = 243).
        folio = db.guest_folios.find_one({"booking_id": "BK-EARLY-SHIFT"})
        assert folio is not None
        assert round(float(folio["total_due"]), 2) == 243.0

        # Posting automático estandarizado: id del catálogo + label resuelto.
        early_postings = [
            p for p in (folio.get("postings") or [])
            if p.get("reference_type") == "early_check_in"
        ]
        assert len(early_postings) == 1
        early_posting = early_postings[0]
        assert early_posting["category_id"] == "early_checkin"
        assert early_posting["category"] == "Early Check-In"

        # Conciliación: el monto del turno == total_due final del folio.
        shift = db.reception_shifts.find_one({"prop_id": 991, "status": "open"})
        check_in_txns = [
            t for t in (shift.get("transactions") or [])
            if t.get("type") == "check_in" and t.get("booking_id") == "BK-EARLY-SHIFT"
        ]
        assert len(check_in_txns) == 1
        txn = check_in_txns[0]
        assert round(float(txn["amount"]), 2) == 243.0
        assert round(float(txn["amount"]), 2) == round(float(folio["total_due"]), 2)
