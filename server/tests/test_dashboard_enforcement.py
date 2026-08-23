"""T7 — Enforcement granular de los dashboards tácticos (frontera de seguridad).

Cada dashboard es un informe con su propio código de permiso
``reports.<dominio>.<informe>.read``. Ocultar el ítem en el menú es solo
cosmético: la frontera real es que el ENDPOINT exija el código fino. Un rol
con el permiso grueso del módulo (``rates.read``, ``billing.read``,
``housekeeping.read``, ``reservations.read``) pero SIN el código fino debe
recibir 403 aunque adivine la URL desde las devtools del navegador.

El rol ``super_admin`` bypassa vía ``*.*`` (no se testea aquí: ya está cubierto
por ``test_hotel_permissions`` / ``user_has_permission``).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from passlib.context import CryptContext

# (endpoint, permiso grueso del módulo, permiso fino del informe)
DASHBOARDS = [
    ("/api/management/rates/analytics/room-performance", "rates.read", "reports.rates.adr.read"),
    ("/api/management/rates/analytics/rate-calendar", "rates.read", "reports.rates.calendar.read"),
    ("/api/stay/requests/analytics?prop_id=1", "reservations.read", "reports.requests.read"),
    ("/api/housekeeping/dashboard?prop_id=1", "housekeeping.read", "reports.housekeeping.dashboard.read"),
    ("/api/housekeeping/operations/analytics?prop_id=1", "housekeeping.read", "reports.housekeeping.operations.read"),
    ("/api/housekeeping/room-status/analytics?prop_id=1", "housekeeping.read", "reports.housekeeping.matrix.read"),
    ("/api/billing/analytics/invoices?prop_id=1", "billing.read", "reports.billing.invoices.read"),
    ("/api/billing/analytics/payments?prop_id=1", "billing.read", "reports.billing.payments.read"),
    # Estratégicos TAF14: el permiso grueso (reports.read) NO abre las vistas.
    # Vista B (cartera) exige el permiso de cartera (exclusivo de dirección);
    # Vista A (hotel) el de hotel. Un permiso NO abre la otra vista.
    ("/api/strategic/portfolio", "reports.read", "reports.strategic.portfolio.read"),
    ("/api/strategic/markets", "reports.read", "reports.strategic.portfolio.read"),
    ("/api/strategic/hotel/1", "reports.read", "reports.strategic.read"),
]

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_user(db, username: str, role: str) -> None:
    """Insert an active user whose ``primary_role`` resolves to ``role``."""
    db.users.insert_one(
        {
            "username": username,
            "email": f"{username}@example.com",
            "display_name": username.replace("_", " ").title(),
            "password_hash": _pwd.hash("TestPass123!"),
            "primary_role": role,
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    )


async def _login(client, username: str) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": username, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path,coarse,fine", DASHBOARDS)
async def test_coarse_permission_without_fine_gets_403(client, db, path, coarse, fine):
    """Un rol con el permiso grueso del módulo pero SIN el código fino del
    informe recibe 403 en el endpoint, aunque adivine la URL."""
    role = f"role_coarse_{coarse.replace('.', '_')}"
    username = f"user_coarse_{coarse.replace('.', '_')}"
    db.roles.insert_one(
        {"role_name": role, "display_name": role, "permissions": [coarse], "is_system": True}
    )
    _make_user(db, username, role)
    await _login(client, username)

    resp = await client.get(path)
    assert resp.status_code == 403, (
        f"{path} debe exigir {fine} (no {coarse}); respondió {resp.status_code}: {resp.text}"
    )


@pytest.mark.asyncio
async def test_fine_permission_grants_access_to_mongo_dashboard(client, db):
    """El código fino del informe SÍ abre el endpoint (control positivo sobre
    un dashboard que lee Mongo, sin dependencia de ClickHouse)."""
    role = "role_fine_matrix"
    username = "user_fine_matrix"
    db.roles.insert_one(
        {
            "role_name": role,
            "display_name": role,
            "permissions": ["reports.housekeeping.matrix.read"],
            "is_system": True,
        }
    )
    _make_user(db, username, role)
    # Migración E: housekeeping gatea por hotel — el código fino debe vivir en
    # un hotel role del prop pedido.
    from bson import ObjectId
    uid = db.users.find_one({"username": username})["_id"]
    hr_id = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "fine_matrix_hotel",
            "display_name": "Fine Matrix",
            "permissions": ["reports.housekeeping.matrix.read"],
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    ).inserted_id
    db.role_assignments.insert_one({"user_id": uid, "prop_id": 1, "role_id": hr_id})
    db.users.update_one({"_id": uid}, {"$set": {"assigned_hotels": [1]}})
    await _login(client, username)

    resp = await client.get("/api/housekeeping/room-status/analytics?prop_id=1")
    assert resp.status_code == 200, resp.text
