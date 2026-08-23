"""Deposit policy gate at check-in (2026-08).

Si el hotel exige depósito (``deposit_required`` + ``deposit_percent`` en
``hotel_policies``, jerarquía rate_plan > room_type > hotel-wide) y la suma de
pagos CONFIRMADOS en ``reservation_payments`` no cubre el mínimo, el check-in
se bloquea. A nivel servicio se lanza ``DepositNotMetError``; a nivel HTTP el
route lo mapea a 409 CONFLICT (no 400 — la reserva es válida, la política no
está satisfecha).

El checkbox informativo ``check_in_deposit_received`` NO satisface el gate:
solo dinero real registrado por billing (turno de caja activo) cuenta como
"pagado". Es la defensa a la puerta de la política de pago por adelantado.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service import (
    DepositNotMetError,
    complete_check_in,
)
from src.app.modules.reservations.service._helpers import utc_now


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_booking(db, booking_id: str, *, total_price: float = 250.0) -> None:
    db.booking_orders.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 991,
            "guest_name": "Deposit Gate Guest",
            "guest_email": "deposit@test.com",
            "status": "confirmed",
            "check_in_date": _days_from_today(0),
            "check_out_date": _days_from_today(2),
            "total_nights": 2,
            "total_price": total_price,
            "currency": "USD",
            "assigned_rooms": [],
            "is_test": True,
        }
    )


def _seed_policy(
    db,
    *,
    prop_id: int = 991,
    required: bool = True,
    percent: int = 30,
) -> None:
    db.hotel_policies.insert_one(
        {
            "prop_id": prop_id,
            "room_type_id": "",
            "rate_plan_id": "",
            "deposit_required": required,
            "deposit_percent": percent,
        }
    )


def _seed_payment(db, booking_id: str, amount: float) -> None:
    db.reservation_payments.insert_one(
        {
            "booking_id": booking_id,
            "prop_id": 991,
            "status": "confirmed",
            "amount": amount,
            "method": "cash",
            "payment_source": "deposit",
            "paid_at": utc_now(),
        }
    )


def _seed_shift(db, prop_id: int = 991) -> None:
    db.reception_shifts.insert_one(
        {
            "prop_id": prop_id,
            "status": "open",
            "shift_type": "morning",
            "start_time": utc_now(),
            "transactions": [],
        }
    )


async def _login(client, username: str, password: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": password},
    )
    assert resp.status_code == 200, resp.text


class TestChecklistReport:
    """El response de ``complete_check_in`` reporta el checklist operativo
    (llaves entregadas, documento verificado, acompañantes) para que el
    check-in masivo avise qué reservas quedaron sin completar y ofrezca el
    link a su detalle. ``has_companions`` respondido como False es una
    respuesta válida ("sin acompañantes"), no un campo faltante: solo es
    incompleto cuando los campos clave no se registraron.
    """

    def test_incomplete_when_checklist_fields_absent(self, db) -> None:
        _seed_booking(db, "BK-CHK-MISSING")
        _seed_shift(db)
        result = complete_check_in("BK-CHK-MISSING", changed_by="recep.prueba")
        assert result["checklist"]["complete"] is False

    def test_complete_when_keys_document_and_companions_set(self, db) -> None:
        _seed_booking(db, "BK-CHK-FULL")
        _seed_shift(db)
        db.booking_orders.update_one(
            {"booking_id": "BK-CHK-FULL"},
            {"$set": {
                "check_in_keys_delivered": True,
                "check_in_document_verified": True,
                "check_in_has_companions": False,
            }},
        )
        result = complete_check_in("BK-CHK-FULL", changed_by="recep.prueba")
        assert result["checklist"]["complete"] is True

    def test_answered_no_companions_counts_as_complete(self, db) -> None:
        _seed_booking(db, "BK-CHK-ALONE")
        _seed_shift(db)
        db.booking_orders.update_one(
            {"booking_id": "BK-CHK-ALONE"},
            {"$set": {
                "check_in_keys_delivered": True,
                "check_in_document_verified": True,
                "check_in_has_companions": False,
            }},
        )
        result = complete_check_in("BK-CHK-ALONE", changed_by="recep.prueba")
        assert result["checklist"]["complete"] is True

    def test_missing_document_keeps_incomplete(self, db) -> None:
        _seed_booking(db, "BK-CHK-NODOC")
        _seed_shift(db)
        db.booking_orders.update_one(
            {"booking_id": "BK-CHK-NODOC"},
            {"$set": {
                "check_in_keys_delivered": True,
                "check_in_has_companions": True,
            }},
        )
        result = complete_check_in("BK-CHK-NODOC", changed_by="recep.prueba")
        assert result["checklist"]["complete"] is False


class TestManualChecklistGate:
    """Regla alineada manual vs masivo: el endpoint /complete exige llaves
    entregadas + documento verificado SALVO que el payload declare
    ``express`` (el flujo masivo, que omite el checklist por diseño y lo
    reporta vía el banner post-masivo).
    """

    @pytest.mark.asyncio
    async def test_http_422_when_manual_missing_keys_or_document(self, client, db, admin_user) -> None:
        await _login(client, admin_user["username"], admin_user["password"])
        _seed_shift(db)
        _seed_booking(db, "BK-CHK-MANUAL-422")

        resp = await client.post("/api/management/check-ins/BK-CHK-MANUAL-422/complete?prop_id=991", json={})

        assert resp.status_code == 422, resp.text
        detail = resp.json()["detail"].lower()
        assert "llaves" in detail and "documento" in detail

    @pytest.mark.asyncio
    async def test_http_allows_manual_complete_with_keys_and_document(self, client, db, admin_user) -> None:
        await _login(client, admin_user["username"], admin_user["password"])
        _seed_shift(db)
        _seed_booking(db, "BK-CHK-MANUAL-OK")

        resp = await client.post(
            "/api/management/check-ins/BK-CHK-MANUAL-OK/complete?prop_id=991",
            json={"check_in_keys_delivered": True, "check_in_document_verified": True},
        )

        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_http_allows_express_bulk_without_checklist(self, client, db, admin_user) -> None:
        await _login(client, admin_user["username"], admin_user["password"])
        _seed_shift(db)
        _seed_booking(db, "BK-CHK-EXPRESS")

        resp = await client.post(
            "/api/management/check-ins/BK-CHK-EXPRESS/complete?prop_id=991",
            json={"express": True},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["checklist"]["complete"] is False


class TestDepositGateService:
    def test_no_policy_allows_check_in(self, db) -> None:
        _seed_booking(db, "BK-DEP-NO-POLICY")

        result = complete_check_in("BK-DEP-NO-POLICY", changed_by="recep.prueba")

        assert result["stay_status"] == "checked_in"
        doc = db.booking_orders.find_one({"booking_id": "BK-DEP-NO-POLICY"})
        assert doc["stay_status"] == "checked_in"

    def test_policy_disabled_allows_check_in(self, db) -> None:
        _seed_booking(db, "BK-DEP-DISABLED")
        _seed_policy(db, required=False, percent=30)

        result = complete_check_in("BK-DEP-DISABLED", changed_by="recep.prueba")

        assert result["stay_status"] == "checked_in"

    def test_required_deposit_without_payment_blocked(self, db) -> None:
        # 250 * 30% = 75 → sin pagos, bloqueado
        _seed_booking(db, "BK-DEP-ZERO")
        _seed_policy(db)

        with pytest.raises(DepositNotMetError) as excinfo:
            complete_check_in("BK-DEP-ZERO", changed_by="recep.prueba")

        msg = str(excinfo.value).lower()
        assert "depósito" in msg and "75.00" in msg
        doc = db.booking_orders.find_one({"booking_id": "BK-DEP-ZERO"})
        assert doc.get("stay_status") in (None, "pending")

    def test_partial_payment_blocked(self, db) -> None:
        # 50 < 75 → sigue bloqueado
        _seed_booking(db, "BK-DEP-PARTIAL")
        _seed_policy(db)
        _seed_payment(db, "BK-DEP-PARTIAL", 50.0)

        with pytest.raises(DepositNotMetError):
            complete_check_in("BK-DEP-PARTIAL", changed_by="recep.prueba")

        doc = db.booking_orders.find_one({"booking_id": "BK-DEP-PARTIAL"})
        assert doc.get("stay_status") not in ("checked_in",)

    def test_failed_payments_do_not_count(self, db) -> None:
        # Un pago failed/rechazado NO cubre el mínimo: solo confirmed cuenta
        _seed_booking(db, "BK-DEP-FAILED")
        _seed_policy(db)
        db.reservation_payments.insert_one(
            {
                "booking_id": "BK-DEP-FAILED",
                "prop_id": 991,
                "status": "failed",
                "amount": 75.0,
                "method": "cash",
                "paid_at": utc_now(),
            }
        )

        with pytest.raises(DepositNotMetError):
            complete_check_in("BK-DEP-FAILED", changed_by="recep.prueba")

    def test_min_deposit_met_allows_check_in(self, db) -> None:
        # 75 = mínimo exacto → check-in OK
        _seed_booking(db, "BK-DEP-MET")
        _seed_policy(db)
        _seed_payment(db, "BK-DEP-MET", 75.0)

        result = complete_check_in("BK-DEP-MET", changed_by="recep.prueba")

        assert result["stay_status"] == "checked_in"
        doc = db.booking_orders.find_one({"booking_id": "BK-DEP-MET"})
        assert doc["stay_status"] == "checked_in"

    def test_payment_above_min_allows_check_in(self, db) -> None:
        _seed_booking(db, "BK-DEP-OVER")
        _seed_policy(db)
        _seed_payment(db, "BK-DEP-OVER", 120.0)

        result = complete_check_in("BK-DEP-OVER", changed_by="recep.prueba")

        assert result["stay_status"] == "checked_in"


class TestDepositGateHttp:
    @pytest.mark.asyncio
    async def test_http_409_when_deposit_not_met(self, client, db, admin_user) -> None:
        await _login(client, admin_user["username"], admin_user["password"])
        _seed_shift(db)
        _seed_booking(db, "BK-DEP-HTTP")
        _seed_policy(db)

        resp = await client.post(
            "/api/management/check-ins/BK-DEP-HTTP/complete?prop_id=991",
            # express: el objetivo de este test es el gate de depósito, no el
            # checklist del check-in manual (regla alineada llaves+documento).
            json={"express": True},
        )

        assert resp.status_code == 409, resp.text
        detail = resp.json()["detail"]
        # El detail es estructurado (no texto plano) para que la UI del
        # check-in renderice el banner accionable con el monto faltante.
        assert detail["code"] == "deposit_not_met"
        assert "depósito" in detail["message"].lower()
        assert detail["deposit_percent"] == 30
        assert detail["min_deposit"] == 75.0
        assert detail["paid_total"] == 0.0
        assert detail["missing"] == 75.0
        doc = db.booking_orders.find_one({"booking_id": "BK-DEP-HTTP"})
        assert doc.get("stay_status") not in ("checked_in",)

    @pytest.mark.asyncio
    async def test_http_check_in_ok_when_deposit_met(self, client, db, admin_user) -> None:
        await _login(client, admin_user["username"], admin_user["password"])
        _seed_shift(db)
        _seed_booking(db, "BK-DEP-HTTP-OK")
        _seed_policy(db)
        _seed_payment(db, "BK-DEP-HTTP-OK", 75.0)

        resp = await client.post(
            "/api/management/check-ins/BK-DEP-HTTP-OK/complete?prop_id=991",
            json={"express": True},
        )

        assert resp.status_code == 200, resp.text
        doc = db.booking_orders.find_one({"booking_id": "BK-DEP-HTTP-OK"})
        assert doc["stay_status"] == "checked_in"
