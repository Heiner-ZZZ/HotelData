"""Contrato compuesto de los informes tácticos del dueño (botón INFORMES).

``GET /api/management/reports`` debe devolver el patrón compuesto táctico
(KPIs → serie → tabla de registros paginada), igual que los dashboards de
``kpi_reports.py``: ``summary`` + ``series`` + ``rows`` paginadas con
``total``/``page``/``page_size``/``total_pages``/``has_next``/``has_prev``.
Además conserva los campos de exportación (top_hotels_by_revenue, etc.).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_role(db, role: str, permissions: list[str]) -> None:
    db.roles.insert_one(
        {"role_name": role, "display_name": role, "permissions": permissions, "is_system": True}
    )


def _make_user(db, username: str, role: str, assigned_hotels: list[int] | None = None) -> None:
    doc = {
        "username": username,
        "email": f"{username}@example.com",
        "display_name": username.replace("_", " ").title(),
        "password_hash": _pwd.hash("TestPass123!"),
        "primary_role": role,
        "is_active": True,
        "created_at": datetime.now(UTC),
    }
    if assigned_hotels is not None:
        doc["assigned_hotels"] = assigned_hotels
    db.users.insert_one(doc)


def _seed_facts(db) -> None:
    """Reservas operativas reales repartidas en 3 meses × 2 hoteles.

    El INFORMES táctico se alimenta de ``booking_orders`` (tabla operativa),
    nunca de la fact sintética GA03: eventos = todas las órdenes, reservas =
    confirmadas, revenue = suma de confirmadas.
    """
    orders = [
        # 2026-01: hotel 1 (2 órdenes, 1 confirmada), hotel 2 (1 cancelada)
        {"booking_id": "BK-TEST-20260105", "check_in_date": "2026-01-05", "prop_id": 1, "status": "confirmed", "total_price": 100.0},
        {"booking_id": "BK-TEST-20260112", "check_in_date": "2026-01-12", "prop_id": 1, "status": "cancelled", "total_price": 80.0},
        {"booking_id": "BK-TEST-20260120", "check_in_date": "2026-01-20", "prop_id": 2, "status": "cancelled", "total_price": 60.0},
        # 2026-02: hotel 1 (1 orden, 1 confirmada)
        {"booking_id": "BK-TEST-20260208", "check_in_date": "2026-02-08", "prop_id": 1, "status": "confirmed", "total_price": 150.0},
        # 2026-03: hotel 2 (2 órdenes, 1 confirmada)
        {"booking_id": "BK-TEST-20260302", "check_in_date": "2026-03-02", "prop_id": 2, "status": "confirmed", "total_price": 90.0},
        {"booking_id": "BK-TEST-20260315", "check_in_date": "2026-03-15", "prop_id": 2, "status": "cancelled", "total_price": 70.0},
    ]
    db.booking_orders.insert_many(orders)


async def _login(client, username: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_reports_returns_composite_contract(client, db):
    """KPIs + serie mensual + filas paginadas con metadatos."""
    _make_role(db, "rol_reportes", ["reports.read"])
    _make_user(db, "user_reportes", "rol_reportes", assigned_hotels=[1, 2])
    _seed_facts(db)
    await _login(client, "user_reportes")

    resp = await client.get("/api/management/reports", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    # KPIs (summary plano existente)
    assert payload["total_events"] == 6
    assert payload["reservations_detected"] == 3
    assert payload["gross_revenue"] == 340.0

    # Serie mensual
    series = payload["series"]
    assert series["labels"] == ["2026-01", "2026-02", "2026-03"], series["labels"]
    by_label = {d["label"]: d["data"] for d in series["datasets"]}
    assert by_label["Eventos"] == [3, 1, 2]
    assert by_label["Reservas"] == [1, 1, 1]
    assert by_label["Revenue (USD)"] == [100.0, 150.0, 90.0]

    # Filas paginadas (misma granularidad que la serie: por mes, desc)
    rows = payload["rows"]
    assert len(rows) == 2
    assert rows[0]["month"] == "2026-03"
    assert rows[0]["events"] == 2
    assert rows[1]["month"] == "2026-02"
    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["page_size"] == 2
    assert payload["total_pages"] == 2
    assert payload["has_next"] is True
    assert payload["has_prev"] is False

    # Campos de exportación conservados
    assert len(payload["top_hotels_by_revenue"]) >= 1
    assert isinstance(payload["operational_counts"], list)


@pytest.mark.asyncio
async def test_reports_pagination_second_page(client, db):
    _make_role(db, "rol_reportes2", ["reports.read"])
    _make_user(db, "user_reportes2", "rol_reportes2", assigned_hotels=[1, 2])
    _seed_facts(db)
    await _login(client, "user_reportes2")

    resp = await client.get("/api/management/reports", params={"page": 2, "page_size": 2})
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    rows = payload["rows"]
    assert len(rows) == 1
    assert rows[0]["month"] == "2026-01"
    assert payload["page"] == 2
    assert payload["has_next"] is False
    assert payload["has_prev"] is True


@pytest.mark.asyncio
async def test_reports_respects_assigned_hotels_scoping(client, db):
    """Un rol restringido con assigned_hotels solo ve sus hoteles en
    KPIs, serie y filas (mismo scoping que el resto del módulo partner)."""
    _make_role(db, "rol_hotel1", ["reports.read"])
    _make_user(db, "user_hotel1", "rol_hotel1", assigned_hotels=[1])
    _seed_facts(db)
    await _login(client, "user_hotel1")

    resp = await client.get("/api/management/reports")
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert payload["total_events"] == 3  # solo hotel 1
    assert payload["reservations_detected"] == 2
    assert payload["gross_revenue"] == 250.0

    series = payload["series"]
    assert series["labels"] == ["2026-01", "2026-02"], series["labels"]
    by_label = {d["label"]: d["data"] for d in series["datasets"]}
    assert by_label["Eventos"] == [2, 1]

    assert payload["total"] == 2
    assert all(row["month"] in ("2026-01", "2026-02") for row in payload["rows"])


@pytest.mark.asyncio
async def test_reports_uses_operational_booking_orders_not_fact(client, db):
    """El INFORMES táctico se alimenta de ``booking_orders`` (tabla operativa
    real), no de la fact sintética GA03. Aunque la fact exista en la BD, los
    KPIs/serie/tabla reflejan las reservas operativas.
    """
    _make_role(db, "rol_operativo", ["reports.read"])
    _make_user(db, "user_operativo", "rol_operativo", assigned_hotels=[1, 2])
    # Fact sintética presente (residuos del dataset GA03): debe ser IGNORADA.
    db.fact_hotel_reservations.insert_many([
        {"date_time": "2013-06-05T10:00:00", "prop_id": 1, "reserva_bool": 1, "reservas_brutas_usd": 99999.0, "srch_destination_id": 11, "visitor_location_country_id": 42},
        {"date_time": "2013-05-10T10:00:00", "prop_id": 1, "reserva_bool": 0, "reservas_brutas_usd": 0.0, "srch_destination_id": 11, "visitor_location_country_id": 42},
    ])
    _seed_facts(db)
    await _login(client, "user_operativo")

    resp = await client.get("/api/management/reports")
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    # La fuente declarada es la operativa, nunca la fact.
    assert payload["source_collection"] == "booking_orders", payload["source_collection"]
    # Totales de booking_orders (6 órdenes, 3 confirmadas, 340 USD).
    assert payload["total_events"] == 6
    assert payload["reservations_detected"] == 3
    assert payload["gross_revenue"] == 340.0
    # Ningún label 2012/2013 (la fact sintética no debe aparecer).
    labels = payload["series"]["labels"]
    assert all(not label.startswith("2012") and not label.startswith("2013") for label in labels), labels


@pytest.mark.asyncio
async def test_reports_requires_reports_read(client, db):
    """Un rol sin reports.read no accede al endpoint."""
    _make_role(db, "rol_sin_reportes", ["dashboard.view"])
    _make_user(db, "user_sin_reportes", "rol_sin_reportes")
    await _login(client, "user_sin_reportes")

    resp = await client.get("/api/management/reports")
    assert resp.status_code == 403, resp.text
