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

from datetime import datetime, timezone

import pytest
from passlib.context import CryptContext

# (endpoint, permiso grueso del módulo, permiso fino del informe)
DASHBOARDS = [
    ("/api/management/rates/analytics/room-performance", "rates.read", "reports.rates.adr.read"),
    ("/api/management/rates/analytics/rate-calendar", "rates.read", "reports.rates.calendar.read"),
    ("/api/stay/requests/analytics", "reservations.read", "reports.requests.read"),
    ("/api/housekeeping/dashboard", "housekeeping.read", "reports.housekeeping.dashboard.read"),
    ("/api/housekeeping/operations/analytics", "housekeeping.read", "reports.housekeeping.operations.read"),
    ("/api/housekeeping/room-status/analytics", "housekeeping.read", "reports.housekeeping.matrix.read"),
    ("/api/billing/analytics/invoices", "billing.read", "reports.billing.invoices.read"),
    ("/api/billing/analytics/payments", "billing.read", "reports.billing.payments.read"),
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
            "created_at": datetime.now(timezone.utc),
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
    await _login(client, username)

    resp = await client.get("/api/housekeeping/room-status/analytics")
    assert resp.status_code == 200, resp.text
