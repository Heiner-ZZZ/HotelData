"""TDD contract del late check-out (gracia / fee / aprobación) — fase de definición.

La política y las reglas de la ventana de salida se definen y prueban ANTES
de tocar el flujo de check-out. ``get_late_checkout_context`` y
``validate_late_checkout`` son read-only (espejo exacto de early check-in);
el cableado en ``complete_check_out``, la ruta y la UI del check-out llegan
en la fase de implementación.

Reglas de negocio:
- La salida el día del check-out ANTES de ``check_out_time`` es normal.
- El día del check-out DESPUÉS de la hora, dentro de la cortesía configurada
  (``late_checkout_courtesy_minutes``) → late sin cargo ni aprobación.
- Fuera de la cortesía → requiere aprobación del gerente
  (``check-ins.late_checkout_approve``), motivo y cargo opcional.
- El late check-out es un modo operativo registrado en la salida; nunca mueve
  las fechas comerciales de la reserva ni re-deduce inventario.
- La política es hotel-wide (``late_checkout_*``), mismo contrato que
  ``early_check_in_*``: las filas por tipo de habitación / plan tarifario no
  la pisan.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

import src.app.modules.reservations.service._checkinout._checkout as checkout_module
from src.app.modules.reservations.service._checkinout._checkout import (
    get_late_checkout_context,
    validate_late_checkout,
)
from tests.conftest import login

FIXED_DATE = "2026-08-14"


def _seed_policy(
    db,
    *,
    prop_id: int = 992,
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


def _freeze_clock(monkeypatch, *, hour: int, minute: int) -> None:
    frozen = datetime(2026, 8, 14, hour, minute, tzinfo=UTC)
    monkeypatch.setattr(checkout_module, "local_today", lambda: FIXED_DATE)
    monkeypatch.setattr(checkout_module, "local_now", lambda: frozen, raising=False)


class TestLateCheckoutContext:
    def test_same_day_after_schedule_within_courtesy_is_late_without_approval(self, db, monkeypatch):
        """Salida a las 12:30 con check-out 12:00 y cortesía 60 min: late, sin aprobación."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=12, minute=30)

        context = get_late_checkout_context(992, FIXED_DATE, db=db)

        assert context["enabled"] is True
        assert context["is_late"] is True
        assert context["minutes_after"] == 30
        assert context["requires_approval"] is False
        assert context["check_out_time"] == "12:00"

    def test_beyond_courtesy_requires_approval(self, db, monkeypatch):
        """Salida a las 14:00 (120 min después) supera la cortesía de 60 min."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        context = get_late_checkout_context(992, FIXED_DATE, db=db)

        assert context["is_late"] is True
        assert context["minutes_after"] == 120
        assert context["requires_approval"] is True

    def test_before_schedule_is_normal(self, db, monkeypatch):
        """Salir antes de la hora de check-out nunca es late."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=11, minute=0)

        context = get_late_checkout_context(992, FIXED_DATE, db=db)

        assert context["is_late"] is False
        assert context["minutes_after"] == 0
        assert context["requires_approval"] is False

    def test_other_day_is_not_late(self, db, monkeypatch):
        """La ventana late solo aplica el día del check-out (mismo día, hora pasada)."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        context = get_late_checkout_context(992, "2026-08-15", db=db)

        assert context["is_late"] is False

    def test_disabled_policy_never_late(self, db, monkeypatch):
        """Con la política apagada no existe ventana late: la salida es normal."""
        _seed_policy(db, enabled=False)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        context = get_late_checkout_context(992, FIXED_DATE, db=db)

        assert context["enabled"] is False
        assert context["is_late"] is False

    def test_missing_policy_uses_defaults_without_window(self, db, monkeypatch):
        """Sin fila de política no hay check_out_time que comparar: la salida es normal."""
        _freeze_clock(monkeypatch, hour=13, minute=0)

        context = get_late_checkout_context(992, FIXED_DATE, db=db)

        assert context["enabled"] is True
        assert context["is_late"] is False
        assert context["courtesy_minutes"] == 60
        assert context["default_fee"] == 0.0


class TestValidateLateCheckout:
    def test_late_departure_without_explicit_mode_rejected(self, db, monkeypatch):
        """Un check-out normal no debe esquivar la ventana late por accidente."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=12, minute=30)

        with pytest.raises(ValueError, match="late check-out"):
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode=None,
                approved=False,
                reason="",
                fee=0,
            )

    def test_within_courtesy_accepts_late_courtesy_without_fee(self, db, monkeypatch):
        """Dentro de la cortesía: modo late_courtesy, cargo 0, sin aprobación gerencial."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=12, minute=30)

        mode, fee, reason = validate_late_checkout(
            get_late_checkout_context(992, FIXED_DATE, db=db),
            mode="late_courtesy",
            approved=True,
            reason="",
            fee=0,
        )

        assert mode == "late_courtesy"
        assert fee == 0.0
        assert reason == ""

    def test_beyond_courtesy_rejects_courtesy_mode(self, db, monkeypatch):
        """Fuera de la cortesía, el modo late_courtesy no alcanza: exige aprobación."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError, match="aprobación"):
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode="late_courtesy",
                approved=True,
                reason="",
                fee=0,
            )

    def test_approved_without_reason_rejected(self, db, monkeypatch):
        """La aprobación fuera de cortesía requiere motivo (mismo contrato que early)."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError, match="motivo"):
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode="late_approved",
                approved=True,
                reason="",
                fee=0,
            )

    def test_approved_with_reason_and_fee_ok(self, db, monkeypatch):
        """Aprobación gerencial con motivo y cargo: el modo late_approved pasa."""
        _seed_policy(db, fee=15.0)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        mode, fee, reason = validate_late_checkout(
            get_late_checkout_context(992, FIXED_DATE, db=db),
            mode="late_approved",
            approved=True,
            reason="Huésped espera vuelo de tarde; gerente autorizó la salida",
            fee=15.0,
        )

        assert mode == "late_approved"
        assert fee == 15.0
        assert reason == "Huésped espera vuelo de tarde; gerente autorizó la salida"

    def test_negative_fee_rejected(self, db, monkeypatch):
        """El cargo nunca puede ser negativo."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError, match="negativo"):
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode="late_approved",
                approved=True,
                reason="Motivo válido",
                fee=-5,
            )

    def test_disabled_policy_rejects_explicit_late_mode(self, db, monkeypatch):
        """Con la ventana apagada, un modo late explícito se rechaza con mensaje claro."""
        _seed_policy(db, enabled=False)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError, match="deshabilitado"):
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode="late_approved",
                approved=True,
                reason="Motivo válido",
                fee=0,
            )

    def test_beyond_courtesy_message_tells_what_to_do(self, db, monkeypatch):
        """Fuera de la cortesía el mensaje dice QUÉ hacer: derivar al gerente."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError) as excinfo:
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode="late_courtesy",
                approved=True,
                reason="",
                fee=0,
            )
        message = str(excinfo.value)
        assert "aprobación del gerente" in message
        assert "Derivalo a gerencia" in message
        assert "registrá el modo aprobado con motivo y cargo" in message

    def test_missing_authorization_message_tells_what_to_do(self, db, monkeypatch):
        """Sin autorización explícita el mensaje indica marcarla antes de continuar."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=12, minute=30)

        with pytest.raises(ValueError) as excinfo:
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode=None,
                approved=False,
                reason="",
                fee=0,
            )
        message = str(excinfo.value)
        assert "Marcá la aprobación del late check-out" in message
        assert "antes de continuar con el check-out" in message

    def test_negative_fee_message_tells_what_to_do(self, db, monkeypatch):
        """El cargo negativo indica corregir el monto (mayor o igual a cero)."""
        _seed_policy(db)
        _freeze_clock(monkeypatch, hour=14, minute=0)

        with pytest.raises(ValueError) as excinfo:
            validate_late_checkout(
                get_late_checkout_context(992, FIXED_DATE, db=db),
                mode="late_approved",
                approved=True,
                reason="Motivo válido",
                fee=-5,
            )
        message = str(excinfo.value)
        assert "no puede ser negativo" in message
        assert "Ingresá un monto mayor o igual a cero" in message


# ── Persistencia de la política (PUT/GET /api/management/policies) ──────


def _seed_hotel(db, prop_id: int = 802) -> None:
    db.dim_hotels.insert_one(
        {"prop_id": prop_id, "hotel_name": "Hotel Late Check-out", "display_name": "Hotel Late Check-out"}
    )


def _policies_payload(**overrides) -> dict:
    payload = {
        "prop_id": 802,
        "check_in_time": "15:00",
        "check_out_time": "12:00",
        "cancellation_policy": "",
        "pet_policy": "",
        "children_policy": "",
        "extra_bed_policy": "",
        "payment_policy": "",
        "house_rules": "",
        "cancellation_hours": 48,
        "cancellation_penalty_percent": 100,
        "pets_allowed": False,
        "pet_fee": 0,
        "children_allowed": True,
        "extra_bed_fee": 0,
        "min_stay": 1,
        "max_stay": 30,
        "deposit_percent": 0,
        "deposit_required": False,
        "early_check_in_enabled": True,
        "early_check_in_courtesy_minutes": 60,
        "early_check_in_default_fee": 0,
        "late_checkout_enabled": True,
        "late_checkout_courtesy_minutes": 90,
        "late_checkout_default_fee": 20.0,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_put_policies_saves_late_checkout_fields(client: AsyncClient, admin_user, db) -> None:
    _seed_hotel(db)
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put("/api/management/policies", json=_policies_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["late_checkout_enabled"] is True
    assert body["late_checkout_courtesy_minutes"] == 90
    assert body["late_checkout_default_fee"] == 20.0
    doc = db.hotel_policies.find_one({"prop_id": 802, "room_type_id": {"$in": ["", None]}})
    assert doc["late_checkout_enabled"] is True
    assert doc["late_checkout_courtesy_minutes"] == 90
    assert doc["late_checkout_default_fee"] == 20.0


@pytest.mark.asyncio
async def test_get_policies_returns_late_checkout_defaults(client: AsyncClient, admin_user, db) -> None:
    _seed_hotel(db)
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.get("/api/management/policies?prop_id=802")

    assert response.status_code == 200
    policies = response.json()["policies"]
    assert policies["late_checkout_enabled"] is True
    assert policies["late_checkout_courtesy_minutes"] == 60
    assert policies["late_checkout_default_fee"] == 0.0


@pytest.mark.asyncio
async def test_put_policies_room_type_scope_ignores_late_checkout_fields(
    client: AsyncClient, admin_user, db
) -> None:
    """Late check-out es política hotel-wide: una fila por tipo de habitación no
    debe pisar los valores globales (mismo contrato que early_check_in_*)."""
    _seed_hotel(db)
    await login(client, admin_user["username"], admin_user["password"])
    db.hotel_policies.insert_one(
        {
            "prop_id": 802,
            "room_type_id": "",
            "rate_plan_id": "",
            "season_id": "",
            "late_checkout_enabled": False,
            "late_checkout_courtesy_minutes": 30,
            "late_checkout_default_fee": 5.0,
        }
    )

    response = await client.put(
        "/api/management/policies",
        json=_policies_payload(room_type_id="RT-STD", late_checkout_enabled=True, late_checkout_courtesy_minutes=180),
    )

    assert response.status_code == 200
    room_row = db.hotel_policies.find_one({"prop_id": 802, "room_type_id": "RT-STD"})
    assert "late_checkout_enabled" not in room_row
    assert "late_checkout_courtesy_minutes" not in room_row
    assert "late_checkout_default_fee" not in room_row
    # La fila hotel-wide conserva sus valores globales intactos.
    hotel_row = db.hotel_policies.find_one(
        {"prop_id": 802, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}}
    )
    assert hotel_row["late_checkout_enabled"] is False
    assert hotel_row["late_checkout_courtesy_minutes"] == 30
    assert hotel_row["late_checkout_default_fee"] == 5.0


@pytest.mark.asyncio
async def test_put_policies_clamps_courtesy_and_fee(client: AsyncClient, admin_user, db) -> None:
    """Cortesía se acota a 0–240 y el fee nunca es negativo (parseo defensivo)."""
    _seed_hotel(db)
    await login(client, admin_user["username"], admin_user["password"])

    response = await client.put(
        "/api/management/policies",
        json=_policies_payload(late_checkout_courtesy_minutes=9999, late_checkout_default_fee=-10),
    )

    assert response.status_code == 200
    doc = db.hotel_policies.find_one({"prop_id": 802, "room_type_id": {"$in": ["", None]}})
    assert doc["late_checkout_courtesy_minutes"] == 240
    assert doc["late_checkout_default_fee"] == 0.0
