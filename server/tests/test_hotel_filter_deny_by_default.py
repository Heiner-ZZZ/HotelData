"""Deny-by-default en hotel_filter — fix sistémico del alcance por hotel.

Hallazgo (2026-08): ``assigned_hotels_for_user`` / ``user_can_access_hotel``
trataban ``assigned_hotels`` vacío como "sin restricción" (acceso a TODO el
sistema) para CUALQUIER rol. Los fixes puntuales (onboarding, HR, ownership)
parchearon los puntos de creación, pero la clase de bug completa vivía en
``hotel_filter``: un usuario con rol de hotel y lista vacía veía todos los
hoteles.

La nueva semántica:

- ``None`` → sin restricción (anónimo, super_admin, admin_sistema, cliente)
- ``[]`` → rol restringido SIN hoteles asignados → NO accede a ningún hotel
  (deny por defecto)
- ``[1, 2, 3]`` → esos hoteles

Cubre los tres consumidores del alcance:
1. ``user_can_access_hotel`` → require_prop_permission + partner_hotel_detail
2. ``hotel_filter_from_user`` → list_partner_hotels (propiedades)
3. ``_reports_hotel_match`` → management reports (dashboard)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.partner.services.dashboard.reports import _reports_hotel_match
from src.app.modules.partner.services.properties import list_partner_hotels
from src.app.modules.partner.services.properties.detail import partner_hotel_detail
from src.app.security.hotel_filter import (
    assigned_hotels_for_user,
    hotel_filter_from_user,
    user_can_access_hotel,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(*, role: str, assigned_hotels: list[int] | None = "MISSING") -> dict:
    doc = {
        "username": f"{role}_user",
        "primary_role": role,
        "is_active": True,
        "created_at": _now(),
    }
    if assigned_hotels != "MISSING":
        doc["assigned_hotels"] = assigned_hotels
    return doc


# ── user_can_access_hotel ──


def test_restricted_user_empty_assigned_hotels_denied():
    """RED: rol de hotel con assigned_hotels=[] → NO accede a ningún hotel."""
    user = _user(role="gerente_hotel", assigned_hotels=[])
    assert user_can_access_hotel(user, 1) is False
    assert user_can_access_hotel(user, 999999) is False


def test_restricted_user_missing_assigned_hotels_denied():
    """RED: rol de hotel sin el campo assigned_hotels → deny (era acceso total)."""
    user = _user(role="recepcionista")
    assert user_can_access_hotel(user, 1) is False


def test_restricted_user_with_hotels_scoped():
    """Con assigned_hotels → True solo para sus hoteles."""
    user = _user(role="gerente_hotel", assigned_hotels=[3, 7])
    assert user_can_access_hotel(user, 3) is True
    assert user_can_access_hotel(user, 7) is True
    assert user_can_access_hotel(user, 8) is False


def test_super_admin_empty_assigned_hotels_unrestricted():
    """RED: super_admin conserva el alcance global (override)."""
    user = _user(role="super_admin")
    assert user_can_access_hotel(user, 42) is True


def test_admin_sistema_and_cliente_unrestricted():
    """admin_sistema y cliente (roles sin filtro) siguen con alcance global."""
    for role in ("admin_sistema", "cliente"):
        user = _user(role=role)
        assert user_can_access_hotel(user, 42) is True, role


def test_anonymous_unrestricted():
    """Anónimo (None) se mantiene sin restricción — rutas públicas."""
    assert user_can_access_hotel(None, 42) is True


# ── assigned_hotels_for_user ──


def test_assigned_hotels_semantics_three_states():
    """None = sin restricción · [] = sin hoteles · [..] = hoteles."""
    assert assigned_hotels_for_user(None) is None
    assert assigned_hotels_for_user(_user(role="super_admin")) is None
    assert assigned_hotels_for_user(_user(role="gerente_hotel", assigned_hotels=[])) == []
    assert assigned_hotels_for_user(_user(role="gerente_hotel", assigned_hotels=[3, 7])) == [3, 7]


# ── hotel_filter_from_user ──


def test_hotel_filter_restricted_empty_matches_nothing():
    """RED: el filtro de un rol restringido sin hoteles NO debe ser {} (vacío
    = sin filtro = todos) sino un filtro que no matchea nada."""
    user = _user(role="gerente_hotel", assigned_hotels=[])
    assert hotel_filter_from_user(user) == {"prop_id": {"$in": []}}


def test_hotel_filter_restricted_with_hotels():
    user = _user(role="gerente_hotel", assigned_hotels=[3, 7])
    assert hotel_filter_from_user(user) == {"prop_id": {"$in": [3, 7]}}


def test_hotel_filter_unrestricted_roles_no_filter():
    """super_admin / cliente / None → {} (sin filtro)."""
    assert hotel_filter_from_user(_user(role="super_admin")) == {}
    assert hotel_filter_from_user(_user(role="cliente")) == {}
    assert hotel_filter_from_user(None) == {}


# ── Reports (management dashboard) ──


def test_reports_hotel_match_deny_by_default():
    """RED: restricted-empty → $match que no matchea nada (antes {} = todos)."""
    assert _reports_hotel_match(None) == {}
    assert _reports_hotel_match(_user(role="super_admin")) == {}
    assert _reports_hotel_match(_user(role="gerente_hotel", assigned_hotels=[])) == {
        "$match": {"prop_id": {"$in": []}}
    }
    assert _reports_hotel_match(_user(role="gerente_hotel", assigned_hotels=[3])) == {
        "$match": {"prop_id": {"$in": [3]}}
    }


# ── Superficies de usuario final del mismo bug class ──


def test_list_partner_hotels_denies_empty_scope_user(db):
    """RED: list_partner_hotels con rol restringido sin hoteles → 0 items
    (antes {} = sin filtro = todos los hoteles del sistema)."""
    user = _user(role="gerente_hotel", assigned_hotels=[])
    result = list_partner_hotels("", page=1, page_size=10, user=user)
    assert result["total"] == 0
    assert result["items"] == []


def test_partner_hotel_detail_denies_empty_scope_user(db):
    """RED: partner_hotel_detail con rol restringido sin hoteles → None (404)
    para cualquier hotel (antes user_can_access_hotel True → veía el detalle)."""
    user = _user(role="gerente_hotel", assigned_hotels=[])
    assert partner_hotel_detail(1, user=user) is None


def test_unrestricted_user_still_lists_all(db):
    """Contraparte: super_admin (None scope) no se ve restringido por el fix."""
    user = _user(role="super_admin")
    result = list_partner_hotels("", page=1, page_size=10, user=user)
    assert result["total"] >= 0  # no lanza y devuelve la paginación normal
    assert isinstance(result["items"], list)


# ── API: require_prop_permission con scope vacío ──


@pytest.mark.asyncio
async def test_prop_permission_403_for_restricted_empty_scope(client, db):
    """RED (route-level): usuario con rol que concede hotel.manage_roles pero
    SIN assigned_hotels → 403 por alcance, aunque tenga el permiso a nivel
    global (antes: user_can_access_hotel True → llegaba al chequeo de permiso)."""
    # Catálogo de permisos
    for code in ("hotel.manage_roles", "dashboard.read"):
        db.permissions.insert_one(
            {
                "permission_code": code,
                "description": code,
                "is_system": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )
    # Rol global con el permiso
    db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente",
            "permissions": ["dashboard.read", "hotel.manage_roles"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    )
    # Usuario con rol de hotel pero SIN assigned_hotels (estado corrupto/legacy)
    # que SÍ tiene el permiso a nivel global (si el alcance fallara, llegaría
    # al chequeo de capacidad y el 403 vendría por permiso, no por alcance).
    from passlib.context import CryptContext

    _pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db.users.insert_one(
        {
            "username": "gerente_sin_hoteles",
            "email": "gerente_sin_hoteles@hotel.local",
            "display_name": "Gerente Sin Hoteles",
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "gerente_hotel",
            "is_active": True,
            "created_at": _now(),
        }
    )

    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "gerente_sin_hoteles", "password": "Pass123!"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/management/hotels/1/roles")
    assert resp.status_code == 403
    assert "acceso al hotel" in resp.json()["detail"]
