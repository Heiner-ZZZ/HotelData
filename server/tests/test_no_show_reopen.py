"""Reapertura de una reserva marcada como no-show (autorización de gerente).

Política de llegadas: "Llegada después de que el no-show fue cerrado → reapertura
o autorización de gerente; no check-in normal". La recepción NO puede reabrir
por sí sola: se exige el permiso gerencial ``check-ins.no_show_reopen``
(gerente_hotel / super_admin) además del gate base ``check-ins.manage``.

Efecto de la reapertura:
- ``stay_status`` vuelve a ``pending`` → el check-in vuelve a estar disponible
  (con la ventana de llegada tardía del sprint anterior).
- El folio de penalización se RETIRA: si solo contiene la penalización
  (``reference_type=no_show_penalty``) se elimina por completo; si arrastra
  pagos u otros cargos la penalización se revierte con un ``charge_reversal``
  (evento compensatorio inmutable) y el folio se conserva para que el gerente
  lo gestione en Facturación.
- Queda traza en la reserva (``no_show_reopened_at/by/reason`` +
  ``no_show_penalty_removed*``), en ``booking_status_history`` y en el audit
  log.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from bson import ObjectId
from passlib.context import CryptContext

import src.app.modules.reservations.service._checkinout._checkin as checkin_module
from scripts.init_security_model_ga03 import PERMISSION_CATALOG, ROLE_PERMISSION_CODES
from scripts.sync_role_permissions import ROLE_PERMISSIONS
from src.app.core.timezone import local_today
from src.app.modules.reservations.service._checkinout import complete_check_in
from src.app.modules.reservations.service.no_show import reopen_no_show
from tests.conftest import login

REOPEN_PERMISSION = "check-ins.no_show_reopen"
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────── Catálogo canónico ───────────────────────────


def test_reopen_permission_is_canonical_and_manager_only() -> None:
    """La reapertura es una autorización gerencial, no CRUD de front desk."""
    catalog_codes = {code for code, _ in PERMISSION_CATALOG}
    assert REOPEN_PERMISSION in catalog_codes
    assert REOPEN_PERMISSION in ROLE_PERMISSION_CODES["super_admin"]
    assert REOPEN_PERMISSION in ROLE_PERMISSION_CODES["gerente_hotel"]
    assert REOPEN_PERMISSION not in ROLE_PERMISSION_CODES["recepcionista"]
    assert REOPEN_PERMISSION in ROLE_PERMISSIONS["gerente_hotel"]
    assert REOPEN_PERMISSION not in ROLE_PERMISSIONS["recepcionista"]


def test_stay_state_machine_defines_reopen_as_only_no_show_exit() -> None:
    """El state machine de Stay define la reapertura (no_show → pending) como
    la ÚNICA salida del no-show; el resto de transiciones inválidas siguen
    bloqueadas."""
    from src.app.core.state_machine import stay_sm

    assert stay_sm.can_transition("no_show", "pending")
    assert stay_sm.get_valid_next_states("no_show") == ["pending"]
    # El guard del servicio reusa la máquina: pending/pending no es reapertura.
    assert not stay_sm.can_transition("pending", "pending")
    assert not stay_sm.can_transition("checked_in", "no_show")
    assert not stay_sm.can_transition("no_show", "checked_in")
    assert not stay_sm.can_transition("no_show", "checked_out")


# ─────────────────────────── Helpers ───────────────────────────


def _days_from_today(n: int) -> str:
    return (date.fromisoformat(local_today()) + timedelta(days=n)).isoformat()


def _seed_booking(db, booking_id: str = "BK-REOPEN-1", *, stay_status: str = "no_show", **extra) -> None:
    doc = {
        "booking_id": booking_id,
        "prop_id": 991,
        "guest_name": "Reopen Guest",
        "guest_email": "reopen@test.com",
        "status": "confirmed",
        "check_in_date": _days_from_today(-1),
        "check_out_date": _days_from_today(2),
        "total_nights": 3,
        "total_price": 300.0,
        "currency": "USD",
        "stay_status": stay_status,
        "no_show_penalty_amount": 100.0,
        "no_show_penalty_percent": 100,
        "no_show_processed_at": datetime.now(UTC),
        "no_show_processed_by": "no_show_scheduler",
        "is_test": True,
        **extra,
    }
    db.booking_orders.insert_one(doc)


def _seed_folio(
    db,
    booking_id: str = "BK-REOPEN-1",
    *,
    penalty: float = 100.0,
    with_payment: bool = False,
) -> None:
    """Seed a no-show penalty folio con la forma real (``postings``).

    - ``with_payment=False`` → folio penalty-only (el caso borrable).
    - ``with_payment=True`` → folio con penalización + pago (el folio se
      conserva y la penalización se revierte).
    """
    postings: list[dict] = [
        {
            "posting_id": ObjectId(),
            "type": "charge",
            "category": "No-Show",
            "category_id": "no_show",
            "concept": "No-show — Penalización del 100% de 1 noche",
            "amount": penalty,
            "quantity": 1,
            "unit_price": penalty,
            "reference_id": booking_id,
            "reference_type": "no_show_penalty",
            "posted_at": datetime.now(UTC),
        }
    ]
    total_payments = 0.0
    if with_payment:
        postings.append(
            {
                "posting_id": ObjectId(),
                "type": "payment",
                "category": "Card",
                "concept": "Pago de penalización",
                "amount": penalty,
                "quantity": 1,
                "unit_price": penalty,
                "reference_id": "PAY-REOPEN-1",
                "reference_type": "payment",
                "posted_at": datetime.now(UTC),
            }
        )
        total_payments = penalty
    db.guest_folios.insert_one(
        {
            "booking_id": booking_id,
            "folio_number": f"FL-NS-{booking_id}",
            "prop_id": 991,
            "guest_name": "Reopen Guest",
            "status": "open",
            "total_room": 0.0,
            "total_charges": penalty,
            "total_discounts": 0.0,
            "total_payments": total_payments,
            "total_due": penalty - total_payments,
            "postings": postings,
            "posting_count": len(postings),
            "created_at": datetime.now(UTC),
            "is_test": True,
        }
    )


def _seed_receptionist(db) -> dict[str, str]:
    """Recepcionista con ``check-ins.manage`` pero SIN el permiso gerencial."""
    role_id = db.roles.insert_one(
        {
            "role_name": "recepcionista",
            "display_name": "Recepcionista",
            "permissions": ["check-ins.manage"],
            "is_system": True,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id
    password = "ReceptionPass123!"
    db.users.insert_one(
        {
            "username": "recepcionista_reopen_test",
            "email": "recepcionista_reopen_test@hotel.local",
            "display_name": "Recepcionista Reopen Test",
            "password_hash": _pwd.hash(password),
            "primary_role": "recepcionista",
            "role_ids": [role_id],
            "assigned_hotels": [991],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    )
    # Migración E: asignación por-hotel para que el gate prop pase y la
    # negación venga de la autorización gerencial (no_show_reopen).
    user = db.users.find_one({"username": "recepcionista_reopen_test"})
    hotel_role_id = db.hotel_roles.insert_one(
        {
            "prop_id": 991,
            "name": "recepcionista",
            "display_name": "Recepcionista",
            "permissions": ["check-ins.manage"],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id
    db.role_assignments.insert_one(
        {"user_id": user["_id"], "role_id": hotel_role_id, "prop_id": 991}
    )
    return {"username": "recepcionista_reopen_test", "password": password}


# ─────────────────────────── Ruta: contrato ───────────────────────────


@pytest.mark.asyncio
async def test_reopen_requires_auth(client, db) -> None:
    _seed_booking(db)
    response = await client.post(
        "/api/management/bookings/BK-REOPEN-1/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó después del cierre del no-show"},
    )
    assert response.status_code in (303, 401, 403)
    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-1"})
    assert doc["stay_status"] == "no_show"


@pytest.mark.asyncio
async def test_receptionist_cannot_reopen(client, db) -> None:
    """Tiene check-ins.manage pero NO la autorización gerencial → 403."""
    credentials = _seed_receptionist(db)
    _seed_booking(db)
    assert await login(client, credentials["username"], credentials["password"]) == 200

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-1/reopen-no-show?prop_id=991",
        json={"reason": "Intento de recepción sin autorización gerencial"},
    )

    assert response.status_code == 403
    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-1"})
    assert doc["stay_status"] == "no_show"
    assert "no_show_reopened_at" not in doc


@pytest.mark.asyncio
async def test_reopen_returns_404_for_unknown_booking(client, admin_user) -> None:
    await login(client, admin_user["username"], admin_user["password"])
    response = await client.post(
        "/api/management/bookings/BK-NOPE/reopen-no-show?prop_id=991",
        json={"reason": "Cualquier motivo"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reopen_rejects_booking_not_marked_no_show(client, admin_user, db) -> None:
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, stay_status="pending")

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-1/reopen-no-show?prop_id=991",
        json={"reason": "No debería reabrir una reserva pending"},
    )

    assert response.status_code == 400
    assert "no-show" in response.json()["detail"].lower()
    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-1"})
    assert doc["stay_status"] == "pending"


@pytest.mark.asyncio
async def test_reopen_requires_reason(client, admin_user, db) -> None:
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db)

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-1/reopen-no-show?prop_id=991",
        json={"reason": "   "},
    )

    assert response.status_code == 400
    assert "motivo" in response.json()["detail"].lower()
    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-1"})
    assert doc["stay_status"] == "no_show"


@pytest.mark.asyncio
async def test_reopen_success_restores_pending_and_removes_penalty_folio(client, admin_user, db) -> None:
    """Folio penalty-only → se elimina por completo; queda traza completa."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db)
    _seed_folio(db)

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-1/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó a las 02:00 tras el cierre; gerente autorizó la reapertura"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["stay_status"] == "pending"
    assert body["booking_id"] == "BK-REOPEN-1"
    assert body["penalty_removed"] is True
    assert body["folio_deleted"] is True
    assert body["folio_number"] == "FL-NS-BK-REOPEN-1"

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-1"})
    assert doc["stay_status"] == "pending"
    assert doc["no_show_reopen_reason"] == "El huésped llegó a las 02:00 tras el cierre; gerente autorizó la reapertura"
    assert doc["no_show_reopened_by"] == admin_user["username"]
    assert doc["no_show_reopened_at"] is not None
    # El folio de penalización ya no existe (solo contenía la penalización).
    assert db.guest_folios.find_one({"booking_id": "BK-REOPEN-1"}) is None
    # Traza de la retirada + penalización histórica conservada en la reserva.
    assert doc["no_show_penalty_removed"] is True
    assert doc["no_show_penalty_removed_at"] is not None
    assert doc["no_show_penalty_removed_by"] == admin_user["username"]
    assert doc["no_show_penalty_amount"] == 100.0

    history = db.booking_status_history.find_one({"booking_id": "BK-REOPEN-1"})
    assert history is not None
    assert "no_show_reopen" in history["reason"]
    assert "folio eliminado" in history["reason"]
    assert history["changed_by"] == admin_user["username"]


@pytest.mark.asyncio
async def test_reopen_reverses_penalty_when_folio_has_payments(client, admin_user, db) -> None:
    """Folio con pago → no se borra; la penalización se revierte (charge_reversal)."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db)
    _seed_folio(db, with_payment=True)

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-1/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó al día siguiente; el pago de la penalización se gestiona en Facturación"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["penalty_removed"] is True
    assert body["folio_deleted"] is False
    assert body["folio_number"] == "FL-NS-BK-REOPEN-1"
    assert body["reversal_amount"] == 100.0

    # El folio se conserva con su historial de pagos intacto…
    folio = db.guest_folios.find_one({"booking_id": "BK-REOPEN-1"})
    assert folio is not None
    assert any(p.get("type") == "payment" for p in folio["postings"])
    # …pero la penalización quedó revertida por un evento compensatorio.
    reversals = [p for p in folio["postings"] if p.get("type") == "charge_reversal"]
    assert len(reversals) == 1
    assert reversals[0]["amount"] == 100.0
    assert reversals[0]["reference_type"] == "no_show_penalty_reversal"
    assert folio["total_charges"] == 0.0
    # El pago que cubría la penalización queda como crédito a favor del
    # huésped (-100): el gerente lo aplica o reembolsa en Facturación.
    assert folio["total_due"] == -100.0

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-1"})
    assert doc["stay_status"] == "pending"
    assert doc["no_show_penalty_removed"] is True

    history = db.booking_status_history.find_one({"booking_id": "BK-REOPEN-1"})
    assert "cargo revertido" in history["reason"]


@pytest.mark.asyncio
async def test_reopen_without_folio_still_succeeds(client, admin_user, db) -> None:
    """No hay folio (read path de recuperación) → reapertura normal, sin error."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db)

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-1/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó después del cierre; no había folio de penalización"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["penalty_removed"] is False
    assert body["folio_deleted"] is False
    assert body["folio_number"] is None

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-1"})
    assert doc["stay_status"] == "pending"
    # Sin folio no se estampa la traza de retirada.
    assert doc.get("no_show_penalty_removed") is None


@pytest.mark.asyncio
async def test_reopen_broadcasts_no_show_reopen_to_team(client, admin_user, db) -> None:
    """Reabrir un no-show real emite un broadcast operativo a la campanita
    (``notification_log`` con ``recipient_email`` vacío, patrón
    ``housekeeping_check_in`` / ``late_checkout_*``) para que recepción y
    housekeeping sepan que el huésped llegará tarde y la reserva volvió a
    ``pending``."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-NS", is_test=False)

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-NS/reopen-no-show?prop_id=991",
        json={"reason": "El huésped avisó que llega tarde; el gerente reabre la estancia"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True

    entry = db.notification_log.find_one(
        {"entity_id": "BK-REOPEN-NS", "notification_type": "no_show_reopen"}
    )
    assert entry is not None
    # Broadcast de equipo: sin destinatario, la campanita la muestra a todo el staff.
    assert entry["recipient_email"] == ""
    assert entry["prop_id"] == 991
    assert entry["entity_type"] == "booking"
    assert entry["status"] == "pending"
    message = entry["message"]
    assert "Reopen Guest" in message
    assert "llegará tarde" in message
    assert "El huésped avisó que llega tarde; el gerente reabre la estancia" in message
    # La penalización se retiró (no había folio) y el mensaje lo refleja.
    assert entry["metadata"]["reopen_reason"] == "El huésped avisó que llega tarde; el gerente reabre la estancia"
    assert entry["metadata"]["reopened_by"] == admin_user["username"]
    assert entry["metadata"]["guest_name"] == "Reopen Guest"
    assert entry["metadata"]["no_show_penalty_removed"] is False
    assert entry["metadata"]["check_in_date"] == _days_from_today(-1)
    assert entry["metadata"]["check_out_date"] == _days_from_today(2)


@pytest.mark.asyncio
async def test_reopen_does_not_broadcast_for_test_booking(client, admin_user, db) -> None:
    """Las reservas ``is_test`` no emiten broadcast (misma regla del check-in):
    la campanita no debe ensuciarse con datos de prueba."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-TEST", is_test=True)

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-TEST/reopen-no-show?prop_id=991",
        json={"reason": "Reserva de prueba reabierta"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert db.notification_log.count_documents(
        {"entity_id": "BK-REOPEN-TEST", "notification_type": "no_show_reopen"}
    ) == 0


# ──────────── Inventario: re-deducción al reabrir / al check-in ────────────


def _seed_inventory(
    db,
    *,
    room_type_id: str = "RT-DBL",
    check_in_date: str = "",
    nights: int = 3,
    available: int = 5,
) -> None:
    """Sembrar filas del calendario de inventario para una estancia."""
    start = date.fromisoformat(check_in_date or _days_from_today(-1))
    for i in range(nights):
        db.room_inventory_calendar.insert_one(
            {
                "prop_id": 991,
                "room_type_id": room_type_id,
                "date": (start + timedelta(days=i)).isoformat(),
                "total_rooms": 10,
                "available_rooms": available,
                "is_available": True,
            }
        )


def _inventory_rows(db, *, room_type_id: str = "RT-DBL", start_date: str = "", nights: int = 3) -> list[dict]:
    """Filas del calendario en orden de fecha (pueden incluir None si falta una noche)."""
    start = date.fromisoformat(start_date or _days_from_today(-1))
    rows: list[dict] = []
    for i in range(nights):
        row = db.room_inventory_calendar.find_one(
            {"prop_id": 991, "room_type_id": room_type_id, "date": (start + timedelta(days=i)).isoformat()}
        )
        rows.append(row)
    return rows


@pytest.mark.asyncio
async def test_reopen_rededucts_inventory(client, admin_user, db) -> None:
    """Reabrir una no-show vuelve a tomar las noches que el no-show liberó.

    El no-show ejecutó ``_restore_inventory``; la reapertura debe re-deducir
    TODA la estancia antes de mutar la reserva y dejar la marca de idempotencia
    para que el check-in posterior no vuelva a deducir.
    """
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-INV", room_type_id="RT-DBL", rooms=1)
    _seed_inventory(db, room_type_id="RT-DBL")

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-INV/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó después del cierre; el gerente reabre la estancia"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["inventory_re_deducted"] is True

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-INV"})
    assert doc["stay_status"] == "pending"
    assert doc["inventory_re_deducted_at"] is not None
    assert doc["inventory_re_deducted_by"] == admin_user["username"]

    # Cada noche de la estancia quedó re-deducida (5 → 4), sin tocar el folio.
    rows = _inventory_rows(db)
    assert len(rows) == 3
    assert all(r is not None and r["available_rooms"] == 4 for r in rows)


@pytest.mark.asyncio
async def test_reopen_fails_when_inventory_insufficient(client, admin_user, db) -> None:
    """Una noche sin stock → la reapertura falla (400) y NADA se escribe.

    ``_deduct_inventory`` valida toda la estancia en una transacción: si una
    noche ya fue re-vendida, la reserva se queda en ``no_show`` (no puede
    re-alojarse en noches sin disponibilidad) y el calendario queda intacto.
    """
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-NOINV", room_type_id="RT-DBL", rooms=2)
    _seed_inventory(db, room_type_id="RT-DBL")
    db.room_inventory_calendar.update_one(
        {"prop_id": 991, "room_type_id": "RT-DBL", "date": _days_from_today(0)},
        {"$set": {"available_rooms": 0}},
    )

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-NOINV/reopen-no-show?prop_id=991",
        json={"reason": "Prueba de inventario insuficiente"},
    )

    assert response.status_code == 400
    assert "inventario" in response.json()["detail"].lower()

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-NOINV"})
    assert doc["stay_status"] == "no_show"
    assert doc.get("inventory_re_deducted_at") is None
    assert doc.get("no_show_reopened_at") is None

    # La transacción abortó: ni la noche insuficiente ni las otras cambiaron.
    rows = _inventory_rows(db)
    assert [r["available_rooms"] for r in rows] == [5, 0, 5]


@pytest.mark.asyncio
async def test_reopen_fails_when_calendar_rows_missing(client, admin_user, db) -> None:
    """Sin filas de calendario para una noche → reapertura rechazada (400)."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-MISSING", room_type_id="RT-DBL", rooms=1)
    _seed_inventory(db, room_type_id="RT-DBL", nights=2)  # la 3ª noche no existe

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-MISSING/reopen-no-show?prop_id=991",
        json={"reason": "Sin filas de calendario"},
    )

    assert response.status_code == 400
    assert "inventario" in response.json()["detail"].lower()

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-MISSING"})
    assert doc["stay_status"] == "no_show"
    assert doc.get("inventory_re_deducted_at") is None

    rows = _inventory_rows(db)
    assert [r["available_rooms"] for r in rows if r is not None] == [5, 5]


def test_checkin_rededucts_reopened_booking_without_marker(db) -> None:
    """Red de seguridad: reserva reabierta ANTES del endurecimiento (sin marca
    ``inventory_re_deducted_at``) → el check-in revalida y re-deduce las noches
    antes de registrar la llegada, y estampa la marca."""
    _seed_booking(
        db,
        "BK-REOPEN-CI",
        check_in_date=_days_from_today(-1),
        check_out_date=_days_from_today(2),
        stay_status="pending",
        room_type_id="RT-DBL",
        rooms=1,
        no_show_reopened_at=datetime.now(UTC),
        no_show_reopened_by="gerente.prueba",
    )
    _seed_inventory(db, room_type_id="RT-DBL", check_in_date=_days_from_today(-1))

    result = complete_check_in("BK-REOPEN-CI", changed_by="recep.prueba")

    assert result["stay_status"] == "checked_in"
    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-CI"})
    assert doc["inventory_re_deducted_at"] is not None
    assert doc["inventory_re_deducted_by"] == "recep.prueba"

    rows = _inventory_rows(db, start_date=_days_from_today(-1))
    assert all(r is not None and r["available_rooms"] == 4 for r in rows)


def test_checkin_after_no_show_reopen_stamps_local_actual_arrival(db, monkeypatch) -> None:
    """La llegada tras reapertura conserva el mismo reloj local que el
    check-in normal y el late-arrival post-midnight."""
    frozen = datetime.now(UTC).replace(hour=2, minute=15, second=0, microsecond=0)
    monkeypatch.setattr(checkin_module, "local_today", lambda: frozen.strftime("%Y-%m-%d"))
    monkeypatch.setattr(checkin_module, "local_now", lambda: frozen, raising=False)
    _seed_booking(
        db,
        "BK-REOPEN-LOCAL-CLOCK",
        check_in_date=_days_from_today(-1),
        check_out_date=_days_from_today(2),
        room_type_id="",
        rooms=1,
    )
    # El documento se crea como no-show y vuelve a pending por reapertura.
    db.booking_orders.update_one(
        {"booking_id": "BK-REOPEN-LOCAL-CLOCK"},
        {"$set": {"stay_status": "no_show"}},
    )
    # No se necesita folio ni inventario para este contrato de reloj.
    reopen_no_show(
        "BK-REOPEN-LOCAL-CLOCK",
        reason="El huésped llegó tras el no-show; gerente autorizó",
        changed_by="gerente.prueba",
    )

    complete_check_in("BK-REOPEN-LOCAL-CLOCK", changed_by="recep.prueba")

    booking = db.booking_orders.find_one({"booking_id": "BK-REOPEN-LOCAL-CLOCK"})
    assert booking["check_in_mode"] == "late_arrival"
    assert booking["check_in_date_actual"] == frozen.strftime("%Y-%m-%d")
    assert booking["check_in_time_actual"] == "02:15"


def test_checkin_does_not_rededuct_when_marker_present(db) -> None:
    """Con ``inventory_re_deducted_at`` (reapertura nueva) el check-in NO
    vuelve a deducir: el inventario ya quedó tomado al reabrir."""
    _seed_booking(
        db,
        "BK-REOPEN-CI2",
        check_in_date=_days_from_today(-1),
        check_out_date=_days_from_today(2),
        stay_status="pending",
        room_type_id="RT-DBL",
        rooms=1,
        no_show_reopened_at=datetime.now(UTC),
        inventory_re_deducted_at=datetime.now(UTC),
    )
    _seed_inventory(db, room_type_id="RT-DBL", check_in_date=_days_from_today(-1))

    result = complete_check_in("BK-REOPEN-CI2", changed_by="recep.prueba")

    assert result["stay_status"] == "checked_in"
    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-CI2"})
    assert doc["inventory_re_deducted_at"] is not None

    rows = _inventory_rows(db, start_date=_days_from_today(-1))
    assert all(r is not None and r["available_rooms"] == 5 for r in rows)


# ───────── Ventana de reapertura: hoy o ayer con estadía vigente ─────────


@pytest.mark.asyncio
async def test_reopen_allowed_for_yesterday_checkin_with_active_stay(client, admin_user, db) -> None:
    """Borde de la ventana: check-in de AYER con check-out sin vencer → permitido."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-YEST", check_in_date=_days_from_today(-1), check_out_date=_days_from_today(2))

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-YEST/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó esta mañana; la estadía sigue vigente"},
    )

    assert response.status_code == 200
    assert response.json()["stay_status"] == "pending"


@pytest.mark.asyncio
async def test_reopen_blocked_when_checkin_more_than_one_day_late(client, admin_user, db) -> None:
    """Check-in de hace 2+ días: la ventana de reapertura cerró (400) y la
    reserva queda intacta en ``no_show`` — reabrir una estadía de otras fechas
    colapsaría inventario y folios."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-2D", check_in_date=_days_from_today(-2), check_out_date=_days_from_today(1))

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-2D/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó con dos días de retraso"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "ventana" in detail and "retraso" in detail

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-2D"})
    assert doc["stay_status"] == "no_show"
    assert doc.get("no_show_reopened_at") is None
    assert doc.get("inventory_re_deducted_at") is None


@pytest.mark.asyncio
async def test_reopen_blocked_when_stay_ended(client, admin_user, db) -> None:
    """Estadía ya terminada (check-out de ayer) → no se reabre: no hay estancia
    vigente que reactivar."""
    await login(client, admin_user["username"], admin_user["password"])
    # 1 noche: check-in ayer, check-out ayer → la estadía terminó ayer.
    _seed_booking(db, "BK-REOPEN-END", check_in_date=_days_from_today(-1), check_out_date=_days_from_today(-1))

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-END/reopen-no-show?prop_id=991",
        json={"reason": "El huésped llegó tarde pero igual quería alojarse"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "estadía" in detail and "terminó" in detail

    doc = db.booking_orders.find_one({"booking_id": "BK-REOPEN-END"})
    assert doc["stay_status"] == "no_show"
    assert doc.get("no_show_reopened_at") is None


@pytest.mark.asyncio
async def test_reopen_blocked_message_guides_to_new_reservation(client, admin_user, db) -> None:
    """El mensaje de ventana cerrada orienta al usuario a una acción concreta
    (ajustar fechas / nueva reserva), no a un flujo que ya no aplica."""
    await login(client, admin_user["username"], admin_user["password"])
    _seed_booking(db, "BK-REOPEN-FAR", check_in_date=_days_from_today(-5), check_out_date=_days_from_today(-3))

    response = await client.post(
        "/api/management/bookings/BK-REOPEN-FAR/reopen-no-show?prop_id=991",
        json={"reason": "Caso muy antiguo"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    # Check-in 5 días tarde → primero la ventana de retraso, no la de estadía.
    assert "ajustá las fechas o creá una reserva nueva" in detail


# ─────────────── Ventana compartida con el calendario ───────────────
# ``reopen_window_reason`` es la MISMA regla que el guard de ``reopen_no_show``
# y la que el calendario de Recepción expone por reserva para marcar los
# no-shows reabribles y ocultar la acción en los antiguos.


def test_reopen_window_reason_allows_today_or_yesterday_with_active_stay() -> None:
    """Check-in de HOY o AYER con check-out vigente → reabrible (None)."""
    from src.app.modules.reservations.service.no_show import reopen_window_reason

    assert reopen_window_reason(
        {"check_in_date": _days_from_today(0), "check_out_date": _days_from_today(2)}
    ) is None
    assert reopen_window_reason(
        {"check_in_date": _days_from_today(-1), "check_out_date": _days_from_today(1)}
    ) is None


def test_reopen_window_reason_reports_too_late() -> None:
    """Check-in con 2+ días de retraso → la ventana cerró (too_late)."""
    from src.app.modules.reservations.service.no_show import reopen_window_reason

    assert reopen_window_reason(
        {"check_in_date": _days_from_today(-2), "check_out_date": _days_from_today(1)}
    ) == "too_late"


def test_reopen_window_reason_reports_stay_ended() -> None:
    """Check-out vencido → stay_ended (aunque el retraso sea de un día)."""
    from src.app.modules.reservations.service.no_show import reopen_window_reason

    assert reopen_window_reason(
        {"check_in_date": _days_from_today(-1), "check_out_date": _days_from_today(-1)}
    ) == "stay_ended"


def test_reopen_window_reason_lenient_with_missing_dates() -> None:
    """Fechas faltantes/ilegibles no bloquean (lenient, como el guard)."""
    from src.app.modules.reservations.service.no_show import reopen_window_reason

    assert reopen_window_reason({"check_in_date": "", "check_out_date": None}) is None
    assert reopen_window_reason({}) is None
