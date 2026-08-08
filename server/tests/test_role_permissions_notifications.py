"""Bandeja de notificaciones al modificar permisos de un ``hotel_role`` (Fase 2).

Cubre el lado de escritura: cuando ``update_hotel_role`` cambia los permisos
de un rol, se inserta una fila en ``notification_log`` por cada miembro
asignado a ese rol en el hotel, con el mensaje
"Tus permisos en {hotel} cambiaron — revisa el historial", consumida por el
endpoint existente ``GET /api/notifications/my``.

Reglas verificadas:
1. Cambio real de permisos → notificación a los miembros asignados
   (notification_type=role_permissions_changed, status=sent, prop_id,
   role_id, message con el nombre del hotel).
2. Cambio solo de display_name → sin notificaciones.
3. Re-envío de los mismos permisos (sin cambio real) → sin notificaciones.
4. Solo los miembros asignados al rol modificado reciben la notificación
   (staff del hotel sin asignación no).
5. El endpoint de la bandeja expone ``message`` y el ``type_label`` humano.
6. Un miembro sin email se saltea sin romper a los demás.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import AsyncClient
from passlib.context import CryptContext

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.fixture(autouse=True)
def _clean_role_notifications(db):
    """La BD de tests no se dropea entre tests: limpia solo las filas de este
    tipo para que los counts/find_one sean deterministas (el resto de
    notification_log de otras suites queda intacto)."""
    db.notification_log.delete_many({"notification_type": "role_permissions_changed"})
    yield

CATALOG_CODES = [
    "hotel.manage_roles",
    "dashboard.read",
    "reservations.read",
    "reservations.manage",
    "hr.read",
    "account.read",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_catalog(db) -> None:
    for code in CATALOG_CODES:
        db.permissions.insert_one(
            {
                "permission_code": code,
                "description": code,
                "is_system": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )


def _seed_user(db, *, username: str, email: str, assigned_hotels: list[int]) -> ObjectId:
    return db.users.insert_one(
        {
            "username": username,
            "email": email,
            "display_name": username.title(),
            "password_hash": _pwd.hash("Pass123!"),
            "primary_role": "recepcionista",
            "role_ids": [],
            "assigned_hotels": assigned_hotels,
            "is_active": True,
            "created_at": _now(),
        }
    ).inserted_id


def _create_recepcion_role(db, hotel_admin_role) -> str:
    rid = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "recepcionista",
            "display_name": "Recepcionista Hotel 1",
            "permissions": ["dashboard.read", "reservations.read"],
            "based_on_role_id": hotel_admin_role["_id"],
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    return str(rid)


def _assign(db, user_id: ObjectId, role_id: str) -> None:
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": 1,
            "role_id": ObjectId(role_id),
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )


# ── Fixtures (mismo patrón que test_hotel_permissions_api.py) ──


@pytest.fixture
def hotel_permissions_catalog(db):
    _seed_catalog(db)
    return CATALOG_CODES


@pytest.fixture
def hotel_admin_role(db, hotel_permissions_catalog):
    role_id = db.roles.insert_one(
        {
            "role_name": "gerente_hotel",
            "display_name": "Gerente de Hotel",
            "permissions": ["dashboard.read", "reservations.read", "hotel.manage_roles"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    return db.roles.find_one({"_id": role_id})


@pytest.fixture
def hotel_row(db):
    db.dim_hotels.insert_one(
        {"prop_id": 1, "display_name": "Hotel Test 1", "hotel_name": "Hotel Test 1"}
    )
    return db.dim_hotels.find_one({"prop_id": 1})


@pytest.fixture
def hotel_admin_hotel_role(db, hotel_admin_role):
    role_id = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "gerente_hotel",
            "display_name": "Gerente - Hotel 1",
            "permissions": ["dashboard.read", "reservations.read", "hotel.manage_roles"],
            "based_on_role_id": hotel_admin_role["_id"],
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    return db.hotel_roles.find_one({"_id": role_id})


@pytest.fixture
def hotel_admin_user(db, hotel_admin_hotel_role):
    user_id = _seed_user(db, username="gerente1", email="gerente1@hotel.local", assigned_hotels=[1])
    db.users.update_one({"_id": user_id}, {"$set": {"primary_role": "gerente_hotel"}})
    db.role_assignments.insert_one(
        {
            "user_id": user_id,
            "prop_id": 1,
            "role_id": hotel_admin_hotel_role["_id"],
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )
    return db.users.find_one({"_id": user_id})


@pytest_asyncio.fixture
async def logged_hotel_admin(client: AsyncClient, hotel_admin_user):
    resp = await client.post(
        "/api/auth/login",
        json={"identifier": "gerente1", "password": "Pass123!"},
    )
    assert resp.status_code == 200, resp.text
    return client


# ── Tests ──


async def test_permissions_change_notifies_assigned_members(
    logged_hotel_admin: AsyncClient, db, hotel_admin_role, hotel_row
):
    rid = _create_recepcion_role(db, hotel_admin_role)
    staff_id = _seed_user(db, username="staff1", email="staff1@hotel.local", assigned_hotels=[1])
    _assign(db, staff_id, rid)

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"permissions": ["dashboard.read", "reservations.manage", "hr.read"]},
    )
    assert resp.status_code == 200, resp.text

    notif = db.notification_log.find_one(
        {"recipient_email": "staff1@hotel.local", "notification_type": "role_permissions_changed"}
    )
    assert notif is not None, "falta la notificación para el miembro asignado"
    assert notif["status"] == "sent"
    assert notif["prop_id"] == 1
    assert notif["role_id"] == rid
    assert notif["message"] == "Tus permisos en Hotel Test 1 cambiaron — revisa el historial"
    # El gerente (rol distinto) NO recibe la notificación.
    assert db.notification_log.count_documents({"recipient_email": "gerente1@hotel.local"}) == 0


async def test_display_name_only_change_no_notification(
    logged_hotel_admin: AsyncClient, db, hotel_admin_role
):
    rid = _create_recepcion_role(db, hotel_admin_role)
    staff_id = _seed_user(db, username="staff1", email="staff1@hotel.local", assigned_hotels=[1])
    _assign(db, staff_id, rid)

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"display_name": "Recepcionistas"},
    )
    assert resp.status_code == 200, resp.text
    # Sin cambio de permisos → sin notificaciones de tipo role_permissions_changed.
    assert db.notification_log.count_documents(
        {"notification_type": "role_permissions_changed"}
    ) == 0


async def test_identical_permissions_resubmitted_no_notification(
    logged_hotel_admin: AsyncClient, db, hotel_admin_role
):
    rid = _create_recepcion_role(db, hotel_admin_role)
    staff_id = _seed_user(db, username="staff1", email="staff1@hotel.local", assigned_hotels=[1])
    _assign(db, staff_id, rid)

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"permissions": ["dashboard.read", "reservations.read"]},
    )
    assert resp.status_code == 200, resp.text
    # Mismos permisos reenviados → sin cambio real → sin notificaciones.
    assert db.notification_log.count_documents(
        {"notification_type": "role_permissions_changed"}
    ) == 0


async def test_reordered_identical_permissions_no_notification(
    logged_hotel_admin: AsyncClient, db, hotel_admin_role
):
    """Mismo set de permisos reenviado en otro orden (rol legacy con array sin
    normalizar) → sin cambio semántico → sin notificación (comparación por set)."""
    rid = db.hotel_roles.insert_one(
        {
            "prop_id": 1,
            "name": "legacy_rol",
            "display_name": "Rol legacy",
            "permissions": ["reservations.read", "dashboard.read"],  # orden no normalizado
            "based_on_role_id": hotel_admin_role["_id"],
            "is_active": True,
            "is_system": False,
            "created_by": "test",
            "created_at": _now(),
            "updated_at": _now(),
        }
    ).inserted_id
    staff_id = _seed_user(db, username="staff1", email="staff1@hotel.local", assigned_hotels=[1])
    _assign(db, staff_id, str(rid))

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"permissions": ["dashboard.read", "reservations.read"]},  # mismo set, otro orden
    )
    assert resp.status_code == 200, resp.text
    assert db.notification_log.count_documents(
        {"notification_type": "role_permissions_changed"}
    ) == 0


async def test_only_assigned_members_notified(
    logged_hotel_admin: AsyncClient, db, hotel_admin_role, hotel_row
):
    rid = _create_recepcion_role(db, hotel_admin_role)
    staff_id = _seed_user(db, username="staff1", email="staff1@hotel.local", assigned_hotels=[1])
    _assign(db, staff_id, rid)
    # Staff del mismo hotel pero SIN asignación de rol.
    _seed_user(db, username="staff_sin_rol", email="staff_sin_rol@hotel.local", assigned_hotels=[1])

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"permissions": ["dashboard.read", "reservations.manage"]},
    )
    assert resp.status_code == 200, resp.text

    assert db.notification_log.count_documents(
        {"recipient_email": "staff1@hotel.local", "notification_type": "role_permissions_changed"}
    ) == 1
    assert db.notification_log.count_documents({"recipient_email": "staff_sin_rol@hotel.local"}) == 0


async def test_notifications_my_exposes_message_and_label(
    client: AsyncClient, db, hotel_admin_user, hotel_admin_role, hotel_row
):
    """La notificación llega a la bandeja del miembro vía /api/notifications/my."""
    # Rol global "recepcionista" con account.read para que el staff pueda
    # consumir /api/notifications/my (resolución global de require_permission).
    db.roles.insert_one(
        {
            "role_name": "recepcionista",
            "display_name": "Recepcionista",
            "permissions": ["account.read", "dashboard.read"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    )
    rid = _create_recepcion_role(db, hotel_admin_role)
    staff_id = _seed_user(db, username="staff1", email="staff1@hotel.local", assigned_hotels=[1])
    _assign(db, staff_id, rid)

    login_admin = await client.post(
        "/api/auth/login", json={"identifier": "gerente1", "password": "Pass123!"}
    )
    assert login_admin.status_code == 200, login_admin.text

    resp = await client.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"permissions": ["dashboard.read", "reservations.manage", "hr.read"]},
    )
    assert resp.status_code == 200, resp.text

    login_staff = await client.post(
        "/api/auth/login", json={"identifier": "staff1", "password": "Pass123!"}
    )
    assert login_staff.status_code == 200, login_staff.text

    resp = await client.get("/api/notifications/my")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["notification_type"] == "role_permissions_changed"
    assert item["type_label"] == "Permisos del rol actualizados"
    assert item["message"] == "Tus permisos en Hotel Test 1 cambiaron — revisa el historial"
    assert item["status"] == "sent"
    assert item["is_unread"] is True


async def test_member_without_email_skipped_others_notified(
    logged_hotel_admin: AsyncClient, db, hotel_admin_role, hotel_row
):
    rid = _create_recepcion_role(db, hotel_admin_role)
    staff_id = _seed_user(db, username="staff1", email="staff1@hotel.local", assigned_hotels=[1])
    _assign(db, staff_id, rid)
    mute_id = _seed_user(db, username="mudo", email="", assigned_hotels=[1])
    _assign(db, mute_id, rid)

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"permissions": ["dashboard.read", "reservations.manage"]},
    )
    assert resp.status_code == 200, resp.text

    assert db.notification_log.count_documents(
        {"recipient_email": "staff1@hotel.local", "notification_type": "role_permissions_changed"}
    ) == 1
    # Sin email → no se puede notificar; no rompe a los demás.
    assert db.notification_log.count_documents({"recipient_name": "Mudo"}) == 0
