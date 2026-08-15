"""TDD flow: late check-out cableado en ``complete_check_out`` (ventana gobernada).

La ventana se resuelve contra la política del hotel (server-authoritative):

- Salida el día del check-out ANTES de la hora → ``check_out_mode: normal``.
- Después de la hora, dentro de la cortesía → ``late_courtesy`` sin cargo.
- Fuera de la cortesía → ``late_approved``: exige autorización gerencial
  (``check-ins.late_checkout_approve``), motivo y cargo derivado del reloj;
  el fee se postea al folio como evento inmutable (patrón early check-in).
- Sin modo explícito o sin autorización → rechazo (mismo contrato estricto
  que ``validate_early_check_in``).
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

import src.app.modules.reservations.service._checkinout._checkout as checkout_module
from src.app.modules.reservations.service import complete_check_out
from src.app.modules.reservations.service._checkinout._checkout import (
    get_late_checkout_context,
)
from src.app.modules.reservations.service._checkinout._helpers import (
    _notify_staff_window_extension,
)
from src.app.modules.reservations.service._checkout_detail import get_check_out_detail

FIXED_CHECK_IN = "2026-08-14"
FIXED_CHECK_OUT = "2026-08-15"


def _seed_policy(
    db,
    *,
    prop_id: int = 993,
    check_out_time: str = "12:00",
    courtesy_minutes: int = 60,
    enabled: bool = True,
    fee: float = 0.0,
) -> None:
    db.hotel_policies.insert_one(
        {
            "prop_id": prop_id,
            "room_type_id": "",
            "rate_plan_id": "",
            "season_id": "",
            "check_in_time": "15:00",
            "check_out_time": check_out_time,
            "late_checkout_enabled": enabled,
            "late_checkout_courtesy_minutes": courtesy_minutes,
            "late_checkout_default_fee": fee,
        }
    )


def _seed_booking(
    db,
    booking_id: str,
    *,
    prop_id: int = 993,
    check_out_date: str = FIXED_CHECK_OUT,
    is_test: bool = True,
) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": prop_id,
            "guest_name": "Late Guest",
            "guest_email": "late@test.com",
            "check_in_date": FIXED_CHECK_IN,
            "check_out_date": check_out_date,
            "total_price": 218.0,
            "currency": "USD",
            "total_nights": 2,
            "rooms": 1,
            "assigned_rooms": [],
            "status": "confirmed",
            "stay_status": "checked_in",
            "is_test": is_test,
        }
    )


def _seed_folio(db, booking_id: str) -> None:
    db.guest_folios.insert_one(
        {
            "booking_id": booking_id,
            "folio_number": f"FL-{booking_id}",
            "status": "open",
            "total_charges": 0.0,
            "total_discounts": 0.0,
            "total_payments": 0.0,
            "total_due": 0.0,
            "postings": [],
        }
    )


def _seed_open_shift(db, *, prop_id: int = 993) -> str:
    """Turno abierto para que ``register_transaction`` registre el check-out."""
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


def _freeze_clock(monkeypatch, *, hour: int, minute: int) -> None:
    frozen = datetime(2026, 8, 15, hour, minute, tzinfo=UTC)
    monkeypatch.setattr(checkout_module, "local_today", lambda: FIXED_CHECK_OUT)
    monkeypatch.setattr(checkout_module, "local_now", lambda: frozen, raising=False)


class TestWindowExtensionNotification:
    def test_common_helper_preserves_early_and_late_payload_contracts(self, db):
        booking = {"prop_id": 993, "guest_name": "Window Guest"}

        _notify_staff_window_extension(
            "BK-COMMON-EARLY",
            booking,
            window="early_checkin",
            minutes=30,
            policy_time="15:00",
            actual_time="14:30",
            fee=0.0,
            mode="early_courtesy",
        )
        _notify_staff_window_extension(
            "BK-COMMON-LATE",
            booking,
            window="late_checkout",
            minutes=30,
            policy_time="12:00",
            actual_time="12:30",
            fee=0.0,
            mode="late_courtesy",
        )

        early = db.notification_log.find_one({"entity_id": "BK-COMMON-EARLY"})
        late = db.notification_log.find_one({"entity_id": "BK-COMMON-LATE"})

        assert early["notification_type"] == "early_checkin_courtesy"
        assert early["metadata"]["minutes_before"] == 30
        assert early["metadata"]["policy_check_in_time"] == "15:00"
        assert early["metadata"]["actual_check_in_time"] == "14:30"
        assert early["metadata"]["early_checkin_mode"] == "early_courtesy"

        assert late["notification_type"] == "late_checkout_courtesy"
        assert late["metadata"]["minutes_after"] == 30
        assert late["metadata"]["policy_check_out_time"] == "12:00"
        assert late["metadata"]["actual_check_out_time"] == "12:30"
        assert late["metadata"]["late_checkout_mode"] == "late_courtesy"


class TestLateCheckoutFlow:
    def test_before_schedule_is_normal(self, db, monkeypatch):
        """Salir a las 11:00 con check-out 12:00: modo normal, sin fee late."""
        _seed_policy(db)
        _seed_booking(db, "BK-LC-NORMAL")
        _freeze_clock(monkeypatch, hour=11, minute=0)

        result = complete_check_out("BK-LC-NORMAL", changed_by="recep.prueba", keys_returned=True)

        assert result["stay_status"] == "checked_out"
        assert result["check_out_mode"] == "normal"
        assert result["late_checkout_fee"] == 0.0
        booking = db.booking_orders.find_one({"booking_id": "BK-LC-NORMAL"})
        assert booking.get("check_out_mode") is None
        assert booking.get("late_checkout_fee", 0) == 0

    def test_within_courtesy_records_late_courtesy_without_fee(self, db, monkeypatch):
        """Salir a las 12:30 (30 min tarde, cortesía 60): late_courtesy sin cargo."""
        _seed_policy(db)
        _seed_booking(db, "BK-LC-COURTESY")
        _freeze_clock(monkeypatch, hour=12, minute=30)

        result = complete_check_out(
            "BK-LC-COURTESY",
            changed_by="recep.prueba",
            keys_returned=True,
            late_checkout_mode="late_courtesy",
            late_checkout_approved=True,
        )

        assert result["check_out_mode"] == "late_courtesy"
        assert result["late_checkout_fee"] == 0.0
        assert result["late_checkout_minutes"] == 30
        booking = db.booking_orders.find_one({"booking_id": "BK-LC-COURTESY"})
        assert booking["check_out_mode"] == "late_courtesy"
        assert booking["late_checkout_minutes"] == 30
        assert booking["late_checkout_fee"] == 0.0

    def test_late_window_without_explicit_mode_rejected(self, db, monkeypatch):
        """Un check-out sin modo en la ventana late no se completa como normal."""
        _seed_policy(db)
        _seed_booking(db, "BK-LC-STRICT")
        _freeze_clock(monkeypatch, hour=12, minute=30)

        with pytest.raises(ValueError, match="autorización"):
            complete_check_out("BK-LC-STRICT", changed_by="recep.prueba", keys_returned=True)

        booking = db.booking_orders.find_one({"booking_id": "BK-LC-STRICT"})
        assert booking.get("stay_status") == "checked_in"

    def test_beyond_courtesy_rejects_courtesy_mode(self, db, monkeypatch):
        """Fuera de la cortesía (14:00, 120 min), late_courtesy no alcanza."""
        _seed_policy(db)
        _seed_booking(db, "BK-LC-BEYOND")
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError, match="aprobación"):
            complete_check_out(
                "BK-LC-BEYOND",
                changed_by="recep.prueba",
                keys_returned=True,
                late_checkout_mode="late_courtesy",
                late_checkout_approved=True,
            )

    def test_approved_without_authorization_rejected_defense_in_depth(self, db, monkeypatch):
        """Defensa en profundidad: el rol puede mandar late_approved pero sin el
        flag de autorización (computado por el gate de la ruta) se rechaza."""
        _seed_policy(db, fee=20.0)
        _seed_booking(db, "BK-LC-NO-AUTH")
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError, match="Permiso requerido: check-ins.late_checkout_approve"):
            complete_check_out(
                "BK-LC-NO-AUTH",
                changed_by="recep.prueba",
                keys_returned=True,
                late_checkout_mode="late_approved",
                late_checkout_approved=True,
                late_checkout_reason="Gerente aprobó la salida",
                late_checkout_fee=20.0,
                late_checkout_authorized=False,
            )

        booking = db.booking_orders.find_one({"booking_id": "BK-LC-NO-AUTH"})
        assert booking.get("stay_status") == "checked_in"
        assert booking.get("check_out_mode") is None

    def test_approved_records_mode_fee_and_minutes(self, db, monkeypatch):
        """Aprobación gerencial: late_approved con motivo y fee derivado del reloj."""
        _seed_policy(db, fee=20.0)
        _seed_booking(db, "BK-LC-APPROVED")
        _freeze_clock(monkeypatch, hour=14, minute=0)

        result = complete_check_out(
            "BK-LC-APPROVED",
            changed_by="gerente.prueba",
            keys_returned=True,
            late_checkout_mode="late_approved",
            late_checkout_approved=True,
            late_checkout_reason="Huésped espera vuelo de tarde; gerente autorizó",
            late_checkout_fee=20.0,
            late_checkout_authorized=True,
        )

        assert result["check_out_mode"] == "late_approved"
        assert result["late_checkout_fee"] == 20.0
        assert result["late_checkout_minutes"] == 120
        booking = db.booking_orders.find_one({"booking_id": "BK-LC-APPROVED"})
        assert booking["check_out_mode"] == "late_approved"
        assert booking["late_checkout_minutes"] == 120
        assert booking["late_checkout_fee"] == 20.0
        assert booking["check_out_late_checkout_fee"] == 20.0
        assert booking["late_checkout_approved_by"] == "gerente.prueba"
        assert booking["late_checkout_reason"] == "Huésped espera vuelo de tarde; gerente autorizó"
        assert booking["late_checkout_policy_time"] == "12:00"

    def test_approved_posts_fee_to_folio(self, db, monkeypatch):
        """El cargo derivado del reloj se publica en el folio como charge."""
        _seed_policy(db, fee=25.0)
        _seed_booking(db, "BK-LC-FOLIO", is_test=False)
        _seed_folio(db, "BK-LC-FOLIO")
        _freeze_clock(monkeypatch, hour=14, minute=30)

        complete_check_out(
            "BK-LC-FOLIO",
            changed_by="gerente.prueba",
            keys_returned=True,
            late_checkout_mode="late_approved",
            late_checkout_approved=True,
            late_checkout_reason="Cargo aprobado por gerencia",
            late_checkout_fee=25.0,
            late_checkout_authorized=True,
        )

        folio = db.guest_folios.find_one({"booking_id": "BK-LC-FOLIO"})
        late_postings = [
            p for p in (folio.get("postings") or [])
            if p.get("reference_type") == "late_checkout"
        ]
        assert len(late_postings) == 1
        posting = late_postings[0]
        # Posting automático estandarizado: id del catálogo + label resuelto.
        assert posting["category_id"] == "late_checkout"
        assert posting["category"] == "Late Check-Out"
        assert round(float(posting["amount"]), 2) == 25.0
        assert "150 min" in posting.get("concept", "")
        assert round(float(folio.get("total_charges", 0)), 2) == 25.0

    def test_approved_late_fee_reconciles_in_folio_and_shift(self, db, monkeypatch):
        """El fee late aprobado llega a ``total_due`` del folio Y al monto del
        turno: ``register_transaction`` re-lee el folio DESPUÉS del posting (el
        fetch inicial quedaba antes y el reporte de turno sub-colectaba). La
        conciliación exige: shift.amount == folio.total_due (con fee)."""
        _seed_policy(db, fee=25.0)
        _seed_booking(db, "BK-LC-SHIFT", is_test=False)
        _seed_folio(db, "BK-LC-SHIFT")
        _seed_open_shift(db)
        _freeze_clock(monkeypatch, hour=14, minute=30)  # 150 min tras las 12:00

        complete_check_out(
            "BK-LC-SHIFT",
            changed_by="gerente.prueba",
            keys_returned=True,
            late_checkout_mode="late_approved",
            late_checkout_approved=True,
            late_checkout_reason="Cargo aprobado por gerencia",
            late_checkout_fee=25.0,
            late_checkout_authorized=True,
        )

        folio = db.guest_folios.find_one({"booking_id": "BK-LC-SHIFT"})
        # El fee late quedó dentro del total_due del folio (no solo en charges).
        assert round(float(folio["total_due"]), 2) == 25.0

        shift = db.reception_shifts.find_one({"prop_id": 993, "status": "open"})
        check_out_txns = [
            t for t in (shift.get("transactions") or [])
            if t.get("type") == "check_out" and t.get("booking_id") == "BK-LC-SHIFT"
        ]
        assert len(check_out_txns) == 1
        txn = check_out_txns[0]
        # Conciliación: el monto del turno == total_due final del folio (con fee).
        assert round(float(txn["amount"]), 2) == 25.0
        assert round(float(txn["amount"]), 2) == round(float(folio["total_due"]), 2)
        assert round(float(shift.get("total_collected", 0) or 0), 2) == 25.0

    def test_approved_late_checkout_notifies_team_with_real_time(self, db, monkeypatch):
        """``late_approved`` registra en ``notification_log`` la salida extendida
        con la hora real (patrón ``housekeeping_check_in`` del check-in)."""
        _seed_policy(db, fee=25.0)
        _seed_booking(db, "BK-LC-NOTIFY", is_test=False)
        _seed_folio(db, "BK-LC-NOTIFY")
        _freeze_clock(monkeypatch, hour=14, minute=30)  # 150 min tras las 12:00

        complete_check_out(
            "BK-LC-NOTIFY",
            changed_by="gerente.prueba",
            keys_returned=True,
            late_checkout_mode="late_approved",
            late_checkout_approved=True,
            late_checkout_reason="Huésped espera vuelo de tarde",
            late_checkout_fee=25.0,
            late_checkout_authorized=True,
        )

        entry = db.notification_log.find_one(
            {"entity_id": "BK-LC-NOTIFY", "notification_type": "late_checkout_approved"}
        )
        assert entry is not None
        message = entry["message"]
        # Hora REAL de la salida extendida (reloj local congelado).
        assert "14:30" in message
        assert "150 min" in message
        assert "Huésped espera vuelo de tarde" in message
        assert "25.00" in message
        assert entry["metadata"]["minutes_after"] == 150
        assert entry["metadata"]["policy_check_out_time"] == "12:00"
        assert entry["metadata"]["actual_check_out_time"] == "14:30"
        assert round(float(entry["metadata"]["late_checkout_fee"]), 2) == 25.0

    def test_courtesy_late_checkout_notifies_team_without_fee(self, db, monkeypatch):
        """``late_courtesy`` también notifica al equipo: la salida está extendida
        aunque no genere cargo, y la limpieza debe ajustarse igual.

        Entrada ``late_checkout_courtesy`` con la hora real, sin línea de cargo
        y metadata con el modo (traza distinta de ``late_checkout_approved``).
        """
        _seed_policy(db, fee=25.0)
        _seed_booking(db, "BK-LC-COURTESY-NOTIFY", is_test=False)
        _seed_folio(db, "BK-LC-COURTESY-NOTIFY")
        _freeze_clock(monkeypatch, hour=12, minute=30)  # 30 min tras las 12:00, dentro de cortesía

        complete_check_out(
            "BK-LC-COURTESY-NOTIFY",
            changed_by="recep.prueba",
            keys_returned=True,
            late_checkout_mode="late_courtesy",
            late_checkout_approved=True,
        )

        entry = db.notification_log.find_one(
            {"entity_id": "BK-LC-COURTESY-NOTIFY", "notification_type": "late_checkout_courtesy"}
        )
        assert entry is not None
        message = entry["message"]
        # Hora REAL de la salida extendida (reloj local congelado).
        assert "12:30" in message
        assert "30 min" in message
        # Sin cargo: el mensaje lo dice y no hay línea de cargo.
        assert "cortesía" in message
        assert "Cargo:" not in message
        assert entry["metadata"]["late_checkout_mode"] == "late_courtesy"
        assert entry["metadata"]["minutes_after"] == 30
        assert entry["metadata"]["policy_check_out_time"] == "12:00"
        assert entry["metadata"]["actual_check_out_time"] == "12:30"
        assert round(float(entry["metadata"]["late_checkout_fee"]), 2) == 0.0

    def test_late_context_exposes_real_departure_time(self, db, monkeypatch):
        """El contexto late expone ``real_time``: la hora real de la salida
        extendida (reloj local del servidor) — campo legible para recepción
        durante el flujo, además de la notificación."""
        _seed_policy(db)
        _seed_booking(db, "BK-LC-REALTIME")
        _freeze_clock(monkeypatch, hour=14, minute=30)

        context = get_late_checkout_context(
            993,
            FIXED_CHECK_OUT,
        )

        assert context["is_late"] is True
        assert context["minutes_after"] == 150
        assert context["real_time"] == "14:30"
        assert context["check_out_time"] == "12:00"

    def test_check_out_detail_exposes_extended_departure_fields(self, db, monkeypatch):
        """El detalle del check-out expone los campos legibles de la salida
        extendida (estampados al completar, fuente de verdad): hora real
        (``check_out_time_actual``), modo, minutos y hora de política."""
        _seed_policy(db, fee=25.0)
        _seed_booking(db, "BK-LC-DETAIL", is_test=False)
        _seed_folio(db, "BK-LC-DETAIL")
        _freeze_clock(monkeypatch, hour=14, minute=30)  # 150 min tras las 12:00

        complete_check_out(
            "BK-LC-DETAIL",
            changed_by="gerente.prueba",
            keys_returned=True,
            late_checkout_mode="late_approved",
            late_checkout_approved=True,
            late_checkout_reason="Huésped espera vuelo de tarde",
            late_checkout_fee=25.0,
            late_checkout_authorized=True,
        )

        detail = get_check_out_detail("BK-LC-DETAIL")
        assert detail["check_out_mode"] == "late_approved"
        assert detail["check_out_time_actual"] == "14:30"
        assert detail["late_checkout_minutes"] == 150
        assert detail["late_checkout_policy_time"] == "12:00"
        assert round(float(detail["late_checkout_fee"]), 2) == 25.0

    def test_disabled_policy_is_normal_checkout(self, db, monkeypatch):
        """Con la ventana apagada, salir tarde es un check-out normal (sin cargo)."""
        _seed_policy(db, enabled=False)
        _seed_booking(db, "BK-LC-DISABLED")
        _freeze_clock(monkeypatch, hour=14, minute=0)

        result = complete_check_out("BK-LC-DISABLED", changed_by="recep.prueba", keys_returned=True)

        assert result["check_out_mode"] == "normal"
        assert result["late_checkout_fee"] == 0.0
