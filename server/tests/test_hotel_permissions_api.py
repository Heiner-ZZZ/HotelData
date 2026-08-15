"""Fase 2 — API 'Equipo y permisos del hotel' (endpoints por prop_id).

Cubre el CRUD de ``hotel_roles`` (clonar plantilla, ajustar permisos,
activar/desactivar, eliminar) y de ``role_assignments`` (asignar, cambiar
rol, desasignar) bajo ``/api/management/hotels/{prop_id}/roles`` +
``/assignments``, protegidos con ``require_prop_permission("hotel.manage_roles")``.

Guardrails verificados aquí:
- permisos validados contra el catálogo (``permissions``) + read-dependencies.
- unicidad de nombre de rol por hotel (409).
- no borrar un rol con asignaciones activas (409).
- anti self-lockout: el admin NO puede editar/eliminar su propio hotel_role,
  ni modificar/eliminar su propia asignación, ni auto-asignarse (409);
  ``super_admin`` conserva override global.
- las plantillas de solo-sistema (super_admin, admin_sistema, cliente) no
  pueden usarse como base de clonado (400).
- anti-lockout: siempre debe quedar >= 1 admin activo (hotel.manage_roles)
  por hotel al desactivar roles / editar permisos / desasignar (409) —
  incluye cuando actúa super_admin (override no quiebra la invariante).
- 403 si el usuario no tiene hotel.manage_roles o si prop_id está fuera de
  su assigned_hotels.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from bson import ObjectId
from httpx import AsyncClient
from passlib.context import CryptContext

from src.app.modules.hotel_permissions import service

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

CATALOG_CODES = [
    "hotel.manage_roles",
    "dashboard.read",
    "reservations.read",
    "reservations.manage",
    "hr.read",
    "payments.read",
]


def _now() -> datetime:
    return datetime.now(UTC)


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


# ── Fixtures ──


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


# ── Auth ──


async def test_roles_requires_auth(client: AsyncClient):
    resp = await client.get("/api/management/hotels/1/roles")
    assert resp.status_code == 401


async def test_assignments_requires_auth(client: AsyncClient):
    resp = await client.get("/api/management/hotels/1/assignments")
    assert resp.status_code == 401


async def test_roles_forbidden_for_hotel_outside_scope(logged_hotel_admin: AsyncClient):
    # gerente1 solo tiene assigned_hotels [1] → hotel 2 queda fuera de alcance.
    resp = await logged_hotel_admin.get("/api/management/hotels/2/roles")
    assert resp.status_code == 403


async def test_roles_forbidden_without_hotel_manage_roles(client: AsyncClient, db, hotel_permissions_catalog, hotel_admin_role):
    # Rol de hotel SIN hotel.manage_roles + usuario con assignment.
    basic_hotel_role_id = db.hotel_roles.insert_one(
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
    staff_id = _seed_user(db, username="staff_forbidden", email="staff_forbidden@hotel.local", assigned_hotels=[1])
    db.role_assignments.insert_one(
        {
            "user_id": staff_id,
            "prop_id": 1,
            "role_id": basic_hotel_role_id,
            "assigned_by": "test",
            "assigned_at": _now(),
        }
    )

    resp = await client.post("/api/auth/login", json={"identifier": "staff_forbidden", "password": "Pass123!"})
    assert resp.status_code == 200
    resp = await client.get("/api/management/hotels/1/roles")
    assert resp.status_code == 403


# ── hotel_roles CRUD ──


async def test_roles_list_returns_items_templates_and_catalog(logged_hotel_admin: AsyncClient, db):
    resp = await logged_hotel_admin.get("/api/management/hotels/1/roles")
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["name"] == "gerente_hotel" and r["prop_id"] == 1 for r in data["items"])
    assert any(t["role_name"] == "gerente_hotel" for t in data["templates"])
    assert "hotel.manage_roles" in data["permission_codes"]


async def test_roles_create(logged_hotel_admin: AsyncClient, db):
    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={
            "name": "recepcionista",
            "display_name": "Recepcionista Hotel 1",
            "permissions": ["dashboard.read", "reservations.manage"],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "recepcionista"
    assert body["prop_id"] == 1
    # ensure_read_dependencies: reservations.manage implica reservations.read
    assert "reservations.read" in body["permissions"]
    assert db.hotel_roles.count_documents({"prop_id": 1, "name": "recepcionista"}) == 1


async def test_roles_create_clones_template(logged_hotel_admin: AsyncClient, db, hotel_admin_role):
    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista2", "based_on_role_id": str(hotel_admin_role["_id"]), "permissions": []},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["based_on"] == "gerente_hotel"
    assert body["based_on_role_id"] == str(hotel_admin_role["_id"])
    # Sin permissions explícitas → hereda las de la plantilla.
    assert "hotel.manage_roles" in body["permissions"]


async def test_roles_create_invalid_permission_rejected(logged_hotel_admin: AsyncClient):
    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "rol_malo", "permissions": ["no.existe"]},
    )
    assert resp.status_code == 400


async def test_roles_create_duplicate_name_conflict(logged_hotel_admin: AsyncClient, hotel_admin_hotel_role):
    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "gerente_hotel", "permissions": ["dashboard.read"]},
    )
    assert resp.status_code == 409


async def test_roles_update_permissions(logged_hotel_admin: AsyncClient, db):
    """El rol propio está protegido (anti self-lockout) → actualizamos un rol
    del equipo que NO esté asignado al admin que actúa."""
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista", "permissions": ["dashboard.read", "reservations.read"]},
    )
    assert create.status_code == 201, create.text
    rid = create.json()["id"]
    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={
            "display_name": "Recepcionista (editado)",
            "permissions": ["dashboard.read", "reservations.manage", "hr.read"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "editado" in body["display_name"]
    assert "hr.read" in body["permissions"]
    stored = db.hotel_roles.find_one({"_id": ObjectId(rid)})
    assert "hr.read" in stored["permissions"]


async def test_roles_update_own_role_denied(logged_hotel_admin: AsyncClient, hotel_admin_hotel_role):
    """Anti self-lockout: el gerente no puede editar (renombrar/permisos) el rol
    que tiene asignado, aunque el cambio no toque hotel.manage_roles."""
    rid = str(hotel_admin_hotel_role["_id"])
    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={
            "display_name": "Nuevo nombre",
            "permissions": ["dashboard.read", "reservations.read", "hotel.manage_roles"],
        },
    )
    assert resp.status_code == 409
    assert "self-lockout" in resp.json()["detail"]


async def test_roles_cannot_deactivate_own_role(logged_hotel_admin: AsyncClient, hotel_admin_hotel_role):
    """Anti self-lockout: el gerente no puede desactivar el rol que tiene asignado."""
    rid = str(hotel_admin_hotel_role["_id"])
    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"is_active": False},
    )
    assert resp.status_code == 409
    assert "self-lockout" in resp.json()["detail"]


async def test_roles_delete_own_role_denied(logged_hotel_admin: AsyncClient, hotel_admin_hotel_role):
    """Anti self-lockout: no se puede eliminar el rol propio."""
    rid = str(hotel_admin_hotel_role["_id"])
    resp = await logged_hotel_admin.delete(f"/api/management/hotels/1/roles/{rid}")
    assert resp.status_code == 409
    assert "self-lockout" in resp.json()["detail"]


async def test_roles_delete_with_assignments_conflict(logged_hotel_admin: AsyncClient, db):
    """Un rol AJENO con personal asignado no se puede eliminar."""
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista", "permissions": ["dashboard.read", "reservations.read"]},
    )
    rid = create.json()["id"]
    staff_id = _seed_user(db, username="staff_asig", email="staff_asig@hotel.local", assigned_hotels=[1])
    await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(staff_id), "role_id": rid},
    )
    resp = await logged_hotel_admin.delete(f"/api/management/hotels/1/roles/{rid}")
    assert resp.status_code == 409


async def test_roles_delete_without_assignments(logged_hotel_admin: AsyncClient, db):
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "temporal", "permissions": ["dashboard.read"]},
    )
    rid = create.json()["id"]
    resp = await logged_hotel_admin.delete(f"/api/management/hotels/1/roles/{rid}")
    assert resp.status_code == 200
    assert db.hotel_roles.count_documents({"_id": ObjectId(rid)}) == 0


# ── role_assignments CRUD ──


async def test_assignments_list_shape(logged_hotel_admin: AsyncClient, db, hotel_admin_user):
    resp = await logged_hotel_admin.get("/api/management/hotels/1/assignments")
    assert resp.status_code == 200
    data = resp.json()
    assert any(a["user_id"] == str(hotel_admin_user["_id"]) for a in data["assigned"])
    assert data["assigned"][0]["role_name"] == "gerente_hotel"
    assert data["assigned"][0]["username"] == "gerente1"
    assert isinstance(data["unassigned_staff"], list)


async def test_assignments_create(logged_hotel_admin: AsyncClient, db):
    create_role = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista", "permissions": ["dashboard.read", "reservations.read"]},
    )
    role_id = create_role.json()["id"]
    staff_id = _seed_user(db, username="staffx", email="staffx@hotel.local", assigned_hotels=[1])

    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(staff_id), "role_id": role_id},
    )
    assert resp.status_code == 201, resp.text
    assert db.role_assignments.count_documents({"user_id": staff_id, "prop_id": 1}) == 1


async def test_assignments_create_duplicate_conflict(logged_hotel_admin: AsyncClient, hotel_admin_user, hotel_admin_hotel_role):
    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(hotel_admin_user["_id"]), "role_id": str(hotel_admin_hotel_role["_id"])},
    )
    assert resp.status_code == 409


async def test_assignments_create_user_not_in_hotel_rejected(logged_hotel_admin: AsyncClient, db):
    create_role = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista", "permissions": ["dashboard.read"]},
    )
    role_id = create_role.json()["id"]
    # staff en el hotel 2 → no puede asignarse al hotel 1.
    staff_id = _seed_user(db, username="staff_otro", email="staff_otro@hotel.local", assigned_hotels=[2])

    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(staff_id), "role_id": role_id},
    )
    assert resp.status_code == 400


async def test_assignments_create_rejects_user_without_hotel_assignment(logged_hotel_admin: AsyncClient, db):
    """Usuario sin assigned_hotels (ej. hotel_partner de onboarding con solo assigned_prop_id)
    no puede ser asignado a ningún hotel: user_can_access_hotel es permisivo con lista vacía.
    """
    create_role = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "recepcionista", "permissions": ["dashboard.read"]},
    )
    role_id = create_role.json()["id"]
    uid = _seed_user(db, username="sin_hoteles", email="sin_hoteles@hotel.local", assigned_hotels=[])

    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(uid), "role_id": role_id},
    )
    assert resp.status_code == 400


async def test_roles_deactivate_ok_when_another_admin_exists(
    logged_hotel_admin: AsyncClient, db
):
    """El admin puede desactivar el rol de OTRO admin: queda el suyo activo,
    así que el anti-lockout no bloquea (la regla 1 solo protege el rol propio)."""
    second_role = (
        await logged_hotel_admin.post(
            "/api/management/hotels/1/roles",
            json={"name": "gerente2", "permissions": ["dashboard.read", "hotel.manage_roles"]},
        )
    ).json()
    staff_id = _seed_user(db, username="gerente2", email="gerente2@hotel.local", assigned_hotels=[1])
    await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(staff_id), "role_id": second_role["id"]},
    )

    rid = second_role["id"]
    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"is_active": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False


async def test_roles_list_excludes_system_templates(logged_hotel_admin: AsyncClient, db):
    """Las plantillas clonables no incluyen roles de solo-sistema (super_admin, etc.)."""
    for role_name in ("super_admin", "admin_sistema", "cliente"):
        db.roles.insert_one(
            {
                "role_name": role_name,
                "display_name": role_name,
                "permissions": [],
                "is_template": True,
                "is_system": True,
                "created_at": _now(),
            }
        )
    resp = await logged_hotel_admin.get("/api/management/hotels/1/roles")
    names = [t["role_name"] for t in resp.json()["templates"]]
    assert "gerente_hotel" in names
    assert "super_admin" not in names
    assert "admin_sistema" not in names
    assert "cliente" not in names


async def test_assignments_update_role(logged_hotel_admin: AsyncClient, db, hotel_admin_hotel_role):
    recepcion_role = (
        await logged_hotel_admin.post(
            "/api/management/hotels/1/roles",
            json={"name": "recepcionista", "permissions": ["dashboard.read", "reservations.read"]},
        )
    ).json()["id"]
    staff_id = _seed_user(db, username="staffup", email="staffup@hotel.local", assigned_hotels=[1])
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(staff_id), "role_id": recepcion_role},
    )
    assignment_id = create.json()["id"]

    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/assignments/{assignment_id}",
        json={"role_id": str(hotel_admin_hotel_role["_id"])},
    )
    assert resp.status_code == 200, resp.text
    stored = db.role_assignments.find_one({"_id": ObjectId(assignment_id)})
    assert stored["role_id"] == hotel_admin_hotel_role["_id"]


async def test_assignments_cannot_delete_own_assignment(logged_hotel_admin: AsyncClient, db, hotel_admin_user):
    """Anti self-lockout: el gerente no puede desasignarse a sí mismo."""
    assignment = db.role_assignments.find_one({"user_id": hotel_admin_user["_id"], "prop_id": 1})
    resp = await logged_hotel_admin.delete(
        f"/api/management/hotels/1/assignments/{assignment['_id']}"
    )
    assert resp.status_code == 409
    assert "self-lockout" in resp.json()["detail"]


async def test_assignments_delete_non_admin(logged_hotel_admin: AsyncClient, db):
    recepcion_role = (
        await logged_hotel_admin.post(
            "/api/management/hotels/1/roles",
            json={"name": "recepcionista", "permissions": ["dashboard.read", "reservations.read"]},
        )
    ).json()["id"]
    staff_id = _seed_user(db, username="staffdel", email="staffdel@hotel.local", assigned_hotels=[1])
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/assignments",
        json={"user_id": str(staff_id), "role_id": recepcion_role},
    )
    assignment_id = create.json()["id"]

    resp = await logged_hotel_admin.delete(
        f"/api/management/hotels/1/assignments/{assignment_id}"
    )
    assert resp.status_code == 200
    assert db.role_assignments.count_documents({"_id": ObjectId(assignment_id)}) == 0


async def test_assignments_update_own_assignment_denied(logged_hotel_admin: AsyncClient, db, hotel_admin_user):
    """Anti self-lockout: no se puede cambiar el rol de la propia asignación,
    aunque el rol destino también otorgue hotel.manage_roles."""
    create = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "gerente_b", "permissions": ["dashboard.read", "hotel.manage_roles"]},
    )
    other_role_id = create.json()["id"]
    assignment = db.role_assignments.find_one({"user_id": hotel_admin_user["_id"], "prop_id": 1})
    resp = await logged_hotel_admin.put(
        f"/api/management/hotels/1/assignments/{assignment['_id']}",
        json={"role_id": other_role_id},
    )
    assert resp.status_code == 409
    assert "self-lockout" in resp.json()["detail"]


async def test_assignments_self_assign_rejected_at_service(db, hotel_admin_user, hotel_admin_hotel_role):
    """Anti self-lockout (defensa en profundidad): el service rechaza la
    auto-asignación; el chequeo corre ANTES del de duplicado para que el 409
    no sea enmascarado por "el usuario ya tiene un rol" (caso irreproducible
    por API porque el admin siempre tiene asignación)."""
    with pytest.raises(PermissionError, match="self-lockout"):
        service.assign_user_to_role(
            db,
            1,
            user_id=str(hotel_admin_user["_id"]),
            role_id=str(hotel_admin_hotel_role["_id"]),
            assigned_by="gerente1",
            actor_user_id=hotel_admin_user["_id"],
            actor_is_super_admin=False,
        )


async def test_roles_update_requires_actor_context(db, hotel_admin_hotel_role):
    """Contrato anti self-lockout: sin contexto de actor (y sin super admin) la
    regla 1 no podría aplicarse — el service rechaza la mutación en vez de
    no-opear silenciosamente (footgun: un futuro llamador que olvide el actor
    dejaría el guardrail muerto)."""
    with pytest.raises(ValueError):
        service.update_hotel_role(
            db,
            1,
            str(hotel_admin_hotel_role["_id"]),
            display_name="X",
            permissions=None,
            is_active=None,
            actor_user_id=None,
            actor_is_super_admin=False,
        )


async def test_assignments_delete_requires_actor_context(db, hotel_admin_user):
    """Mismo contrato en delete_assignment: sin actor → error de contrato, no
    avanzar silenciosamente a los demás chequeos."""
    assignment = db.role_assignments.find_one({"user_id": hotel_admin_user["_id"], "prop_id": 1})
    with pytest.raises(ValueError):
        service.delete_assignment(
            db,
            1,
            str(assignment["_id"]),
            actor_user_id=None,
            actor_is_super_admin=False,
        )


async def test_roles_create_clone_system_template_rejected(logged_hotel_admin: AsyncClient, db):
    """Regla 2: las plantillas de solo-sistema (super_admin) no pueden usarse
    como base de clonado. Con permisos del catálogo, hoy esto crea el rol (201)
    — el guardrail debe rechazarlo con 400."""
    super_role_id = db.roles.insert_one(
        {
            "role_name": "super_admin",
            "display_name": "Super Admin",
            "permissions": ["dashboard.read", "reservations.manage", "hotel.manage_roles"],
            "is_template": True,
            "is_system": True,
            "created_at": _now(),
        }
    ).inserted_id
    resp = await logged_hotel_admin.post(
        "/api/management/hotels/1/roles",
        json={"name": "clon_admin", "based_on_role_id": str(super_role_id), "permissions": []},
    )
    assert resp.status_code == 400
    assert "solo sistema" in resp.json()["detail"]


async def test_roles_super_admin_override_edits_admin_role(
    client: AsyncClient, db, admin_user, hotel_admin_hotel_role
):
    """Override POSITIVO: super_admin conserva la regla 1 saltada — puede editar
    el rol del único admin del hotel (el anti-lockout no bloquea porque
    hotel.manage_roles se conserva). Protege contra la muerte silenciosa del
    override si is_super_admin se rompiera en algún entorno."""
    resp = await client.post(
        "/api/auth/login", json={"identifier": "admin_test", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200, resp.text
    rid = str(hotel_admin_hotel_role["_id"])
    resp = await client.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={
            "display_name": "Gerente renombrado por SA",
            "permissions": ["dashboard.read", "reservations.read", "hotel.manage_roles"],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "Gerente renombrado por SA"


async def test_roles_deactivate_last_admin_denied_super_admin(
    client: AsyncClient, db, admin_user, hotel_admin_hotel_role
):
    """Regla 3 + override: super_admin conserva override, pero el anti-lockout
    sigue protegiendo la invariante — no puede dejar el último rol admin inactivo."""
    resp = await client.post(
        "/api/auth/login", json={"identifier": "admin_test", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200, resp.text
    rid = str(hotel_admin_hotel_role["_id"])
    resp = await client.put(
        f"/api/management/hotels/1/roles/{rid}",
        json={"is_active": False},
    )
    assert resp.status_code == 409
    assert "administraci" in resp.json()["detail"]


async def test_assignments_delete_last_admin_denied_super_admin(
    client: AsyncClient, db, admin_user, hotel_admin_hotel_role, hotel_admin_user
):
    """Regla 3 + override: super_admin tampoco puede desasignar al ÚNICO admin
    del hotel (la invariante de >=1 admin se mantiene incluso con override)."""
    resp = await client.post(
        "/api/auth/login", json={"identifier": "admin_test", "password": "AdminPass123!"}
    )
    assert resp.status_code == 200, resp.text
    assignment = db.role_assignments.find_one({"user_id": hotel_admin_user["_id"], "prop_id": 1})
    resp = await client.delete(
        f"/api/management/hotels/1/assignments/{assignment['_id']}"
    )
    assert resp.status_code == 409
    assert "administraci" in resp.json()["detail"]
