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

from datetime import UTC, date, datetime, timedelta

import pytest

from src.app.core.timezone import local_today
from src.app.modules.reservations.service._checkinout import (
    complete_check_in,
    complete_check_out,
)
from src.app.modules.reservations.service.late_arrival import declare_late_arrival
from src.app.modules.reservations.service.no_show import (
    auto_process_no_shows,
    process_no_show,
    reopen_no_show,
)
from tests.conftest import login


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
        "created_at": datetime.now(UTC),
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


class TestErrorMessagesGuideToActions:
    """Los mensajes del flujo check-in/no-show apuntan a acciones concretas
    (ajustar fechas, crear reserva, contactar gerencia) en vez de solo
    describir el estado — mismo criterio que la ventana de reapertura."""

    def test_explicit_no_show_message_guides_to_reopen_or_new_booking(self, db):
        """Check-in bloqueado por no-show: el mensaje pide reabrir (gerente),
        ajustar fechas o crear una reserva nueva."""
        _seed_booking(
            db, "BK-MSG-NOSHOW",
            check_in_date=_days_from_today(0),
            check_out_date=_days_from_today(2),
            stay_status="no_show",
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-MSG-NOSHOW", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "no-show" in message
        assert "reabra" in message
        assert "ajustá las fechas" in message
        assert "creá una reserva nueva" in message

    def test_expired_stay_message_guides_to_new_booking(self, db):
        """Estadía vencida sin llegar: el mensaje manda a crear reserva nueva."""
        _seed_booking(
            db, "BK-MSG-EXPIRED",
            check_in_date=_days_from_today(-8),
            check_out_date=_days_from_today(-1),
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-MSG-EXPIRED", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "no-show" in message
        assert "check-out" in message
        assert "creá una reserva nueva" in message

    def test_future_checkin_message_guides_to_wait_or_reschedule(self, db):
        """Check-in con fecha futura: el mensaje dice esperar o ajustar fechas."""
        _seed_booking(
            db, "BK-MSG-FUTURE",
            check_in_date=_days_from_today(1),
            check_out_date=_days_from_today(3),
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-MSG-FUTURE", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "futura" in message
        assert "esperá a la fecha de llegada" in message
        assert "ajustá las fechas" in message

    def test_reopen_of_non_no_show_guides_to_normal_checkin(self, db):
        """Reabrir una reserva que NO es no-show: el mensaje manda al check-in
        normal en vez de describir el estado."""
        _seed_booking(
            db, "BK-MSG-REOPEN",
            check_in_date=_days_from_today(0),
            check_out_date=_days_from_today(2),
            stay_status="pending",
        )

        with pytest.raises(ValueError) as excinfo:
            reopen_no_show("BK-MSG-REOPEN", reason="test", changed_by="gerente")

        message = str(excinfo.value).lower()
        assert "no está marcada como no-show" in message
        assert "check-in normal" in message

    def test_late_arrival_on_no_show_guides_to_reopen(self, db):
        """Declarar llegada tardía sobre un no-show: el mensaje pide la
        reapertura gerencial o una reserva nueva."""
        _seed_booking(
            db, "BK-MSG-LATE",
            check_in_date=_days_from_today(0),
            check_out_date=_days_from_today(2),
            stay_status="no_show",
        )

        with pytest.raises(ValueError) as excinfo:
            declare_late_arrival(db, "BK-MSG-LATE", declared=True)

        message = str(excinfo.value).lower()
        assert "no-show" in message
        assert "reabra" in message
        assert "creá una reserva nueva" in message

    def test_mark_no_show_before_checkin_guides_to_wait(self, db):
        """Marcar no-show antes de la fecha de llegada: el mensaje dice esperar
        al día del check-in o ajustar la fecha."""
        _seed_booking(
            db, "BK-MSG-EARLY-NS",
            check_in_date=_days_from_today(1),
            check_out_date=_days_from_today(3),
        )

        with pytest.raises(ValueError) as excinfo:
            process_no_show("BK-MSG-EARLY-NS", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "antes del check-in" in message
        assert "esperá al día del check-in" in message
        assert "ajustá la fecha de llegada" in message


class TestCheckInFutureDateGuard:
    def test_checkin_blocked_when_checkin_date_is_future(self, db):
        """A future arrival date cannot be checked in before that calendar day."""
        _seed_booking(
            db, "BK-FUTURE-CHECKIN",
            check_in_date=_days_from_today(1),
            check_out_date=_days_from_today(3),
        )

        with pytest.raises(ValueError) as excinfo:
            complete_check_in("BK-FUTURE-CHECKIN", changed_by="recep.prueba")

        message = str(excinfo.value).lower()
        assert "futura" in message or "aún no" in message
        doc = db.booking_orders.find_one({"booking_id": "BK-FUTURE-CHECKIN"})
        assert doc.get("stay_status") in (None, "pending")
        assert doc.get("folio") is None
        assert db.guest_folios.count_documents({"booking_id": "BK-FUTURE-CHECKIN"}) == 0


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

    def test_process_no_show_uses_unique_folio_when_legacy_number_collides(self, db):
        """Un folio de no-show no puede desaparecer por colisión del número.

        El formato histórico ``FL-NS-{booking_id[:8]}`` colisiona para reservas
        que comparten el mismo prefijo (por ejemplo, todas las BK-20260...).
        Aunque Mongo rechace ese número único, el proceso debe elegir otro y
        dejar el folio consultable desde Facturación.
        """
        db.guest_folios.insert_one({
            "booking_id": "BK-OTHER-NS",
            "folio_number": "FL-NS-BK-20260",
            "prop_id": 991,
            "status": "open",
            "total_room": 0.0,
            "total_charges": 1.0,
            "total_discounts": 0.0,
            "total_payments": 0.0,
            "total_due": 1.0,
            "postings": [],
            "posting_count": 0,
        })
        booking_id = "BK-20260808210836-83A0CB0A"
        _seed_booking(
            db,
            booking_id,
            check_in_date=_days_from_today(-3),
            check_out_date=_days_from_today(-1),
        )

        result = process_no_show(booking_id, changed_by="recep.prueba")

        assert result["folio_number"]
        assert result["folio_number"] != "FL-NS-BK-20260"
        folio = db.guest_folios.find_one({"booking_id": booking_id})
        assert folio is not None
        assert folio["folio_number"] == result["folio_number"]
        assert folio["total_due"] == result["penalty_amount"]

    @pytest.mark.asyncio
    async def test_billing_get_recovers_a_missing_folio_for_existing_no_show(self, client, admin_user, db):
        """Un no-show histórico sin folio debe poder abrirse en Facturación.

        El bug original dejó ``stay_status=no_show`` guardado, pero el insert
        del folio falló y el endpoint devolvía 404. La lectura debe recuperar
        el folio idempotentemente a partir de la penalización ya registrada.
        """
        booking_id = "BK-20260808210836-83A0CB0A"
        _seed_booking(
            db,
            booking_id,
            check_in_date=_days_from_today(-3),
            check_out_date=_days_from_today(-1),
            stay_status="no_show",
        )
        db.booking_orders.update_one(
            {"booking_id": booking_id},
            {"$set": {"no_show_penalty_amount": 55.59, "no_show_penalty_percent": 51}},
        )
        await login(client, admin_user["username"], admin_user["password"])

        response = await client.get(f"/api/billing/folios/{booking_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["booking_id"] == booking_id
        assert body["folio_number"].startswith("FL-NS-")
        assert body["total_due"] == 55.59
        assert db.guest_folios.count_documents({"booking_id": booking_id}) == 1

        detail_response = await client.get(f"/api/management/check-ins/{booking_id}/detail")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["folio"] == body["folio_number"]
        assert detail["no_show_penalty_amount"] == 55.59


@pytest.mark.asyncio
async def test_check_in_detail_exposes_reopen_marker_when_reopened(client, admin_user, db) -> None:
    """El detalle de check-in expone la marca de reapertura de no-show.

    Tras ``reopen_no_show`` (el gerente reabrió porque el huésped llegó), el
    endpoint del detalle debe devolver ``no_show_reopened_at/by/reason`` y
    ``no_show_penalty_removed`` para que recepción vea el aviso visual en la
    página de check-in (no es un check-in normal: el huésped llegó tras un
    no-show).
    """
    booking_id = "BK-REOPEN-MARKER"
    _seed_booking(
        db,
        booking_id,
        check_in_date=_days_from_today(0),
        check_out_date=_days_from_today(2),
        stay_status="no_show",
    )
    result = reopen_no_show(
        booking_id,
        reason="El huésped llegó; gerente autorizó la reapertura",
        changed_by="gerente.prueba",
    )
    assert result["ok"] is True

    await login(client, admin_user["username"], admin_user["password"])
    response = await client.get(f"/api/management/check-ins/{booking_id}/detail")

    assert response.status_code == 200
    detail = response.json()
    assert detail["stay_status"] == "pending"
    assert detail["no_show_reopened_at"] is not None
    assert detail["no_show_reopened_by"] == "gerente.prueba"
    assert detail["no_show_reopen_reason"] == "El huésped llegó; gerente autorizó la reapertura"
    assert detail["no_show_penalty_removed"] is False


@pytest.mark.asyncio
async def test_check_in_detail_has_empty_reopen_marker_without_reopen(client, admin_user, db) -> None:
    """Sin reapertura, la marca de reapertura viene vacía (nunca reabierta)."""
    booking_id = "BK-NO-REOPEN-MARKER"
    _seed_booking(
        db,
        booking_id,
        check_in_date=_days_from_today(0),
        check_out_date=_days_from_today(2),
        stay_status="pending",
    )
    await login(client, admin_user["username"], admin_user["password"])
    response = await client.get(f"/api/management/check-ins/{booking_id}/detail")

    assert response.status_code == 200
    detail = response.json()
    assert detail["no_show_reopened_at"] is None
    assert detail["no_show_reopened_by"] == ""
    assert detail["no_show_reopen_reason"] == ""
    assert detail["no_show_penalty_removed"] is False
