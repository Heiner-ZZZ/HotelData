"""Sprint PBAC sync — convergencia de una BD con catálogo desactualizado.

El incidente real: ``socio.gta6`` (gerente_hotel) tenía su rol global en dev
sin ``check-ins.manage`` / ``check-ins.early_approve`` y su clon de
``hotel_roles`` (prop 1) con solo 7 permisos de una era anterior, así que la
sesión no podía aprobar early check-in ni siquiera abrir la vista de check-ins.

Estos tests fijan el contrato del sincronizador canónico
(``scripts/sync_pbac_permissions.py``), derivado SIEMPRE del catálogo
``init_security_model_ga03.py``:

- ``permissions``  → upsert de códigos faltantes del catálogo canónico.
- ``navigation``   → convergencia del árbol con ``NAVIGATION_CATALOG``: los
  nodos nuevos aparecen con sus FKs resueltas (``permission_id`` + ``parent_id``)
  y los huérfanos se reportan SIN eliminar (pueden ser nodos personalizados).
- ``roles``        → ``$set`` del array canónico (los templates globales son
  fuente de verdad; misma semántica que ``sync_role_permissions.py``).
- ``hotel_roles``  → ``$addToSet`` ADITIVO: los clones por hotel admiten
  personalización (mismo cargo ≠ mismos permisos en cada hotel), así que el
  sync suma los códigos del template que faltan pero NUNCA elimina nada.

Idempotente: una segunda pasada no debe modificar documentos.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId

from scripts.init_security_model_ga03 import (
    NAVIGATION_CATALOG,
    PERMISSION_CATALOG,
    ROLE_PERMISSION_CODES,
)
from scripts.sync_pbac_permissions import (
    main,
    sync_all,
    sync_global_roles,
    sync_hotel_roles,
    sync_navigation,
    sync_permission_catalog,
)

NAV_CATALOG_SLUGS = {item["slug"] for item in NAVIGATION_CATALOG}

CANONICAL_CATALOG_CODES = {code for code, _ in PERMISSION_CATALOG}
GERENTE_CANONICAL = set(ROLE_PERMISSION_CODES["gerente_hotel"])

# Estado stale real observado en dev (agosto 2026): el clon de hotel_roles
# del gerente en prop 1 fue creado antes de que existieran los check-ins.*.
STALE_GERENTE_HOTEL_ROLE_PERMS = [
    "dashboard.read",
    "hotel.manage_roles",
    "hotels.manage",
    "hotels.read",
    "reservations.manage",
    "reservations.read",
    "revenue.read",
]

# Rol global stale (37 permisos, sin la familia check-ins.*) — lo que tenía
# ``roles.gerente_hotel`` en dev antes del sync.
STALE_GERENTE_GLOBAL_PERMS = [
    "billing.read",
    "dashboard.read",
    "hotel.manage_roles",
    "hotels.manage",
    "housekeeping.read",
    "hr.directory.manage",
    "hr.directory.read",
    "hr.manage",
    "hr.onboarding.create",
    "hr.portal.read",
    "hr.shifts.manage",
    "hr.shifts.read",
    "inventory.products.cost.manage",
    "inventory.products.cost.read",
    "inventory.read",
    "promotions.manage",
    "promotions.read",
    "properties.approve",
    "properties.read",
    "rates.read",
    "reports.billing.invoices.read",
    "reports.billing.payments.read",
    "reports.download",
    "reports.housekeeping.dashboard.read",
    "reports.housekeeping.matrix.read",
    "reports.housekeeping.operations.read",
    "reports.rates.adr.read",
    "reports.rates.calendar.read",
    "reports.requests.read",
    "reports.strategic.read",
    "reports.tactical.read",
    "reservations.manage",
    "revenue.read",
    "reviews.read",
    "rooms.read",
    "shifts.manage",
    "shifts.read",
]


def _seed_global_role(db, *, role_name: str, permissions: list[str]) -> ObjectId:
    return db.roles.insert_one(
        {
            "role_name": role_name,
            "display_name": role_name.replace("_", " ").title(),
            "permissions": list(permissions),
            "is_system": True,
            "is_template": True,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id


def _seed_hotel_role(
    db,
    *,
    prop_id: int,
    name: str,
    permissions: list[str],
    based_on_role_id: ObjectId | None,
) -> ObjectId:
    return db.hotel_roles.insert_one(
        {
            "prop_id": prop_id,
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "permissions": list(permissions),
            "based_on_role_id": based_on_role_id,
            "is_active": True,
            "is_system": False,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id


def _seed_gerente_user(db, *, role_id: ObjectId) -> dict:
    user_id = db.users.insert_one(
        {
            "username": "socio.gta6",
            "email": "heiner.zambrano.ronquillo@gmail.com",
            "display_name": "Socio GTA6",
            "login_aliases": ["Socio GTA6"],
            "password_hash": "x",
            "primary_role": "gerente_hotel",
            "primary_role_id": role_id,
            "role_ids": [role_id],
            "assigned_hotels": [1],
            "is_active": True,
            "created_at": datetime.now(UTC),
        }
    ).inserted_id
    return {"_id": user_id, "primary_role": "gerente_hotel", "role_ids": [role_id]}


# ── 1. Catálogo de permisos ────────────────────────────────────────────


def test_catalog_sync_upserts_missing_codes(db) -> None:
    """Un código nuevo del catálogo canónico (p.ej. check-ins.early_approve)
    ausente en la BD debe ser creado por el sync."""
    db.permissions.insert_one(
        {"permission_code": "check-ins.manage", "description": "x", "is_system": True}
    )
    assert db.permissions.count_documents({}) == 1

    summary = sync_permission_catalog(db)

    stored = {p["permission_code"] for p in db.permissions.find({}, {"permission_code": 1})}
    assert CANONICAL_CATALOG_CODES <= stored
    assert summary["codes_upserted"] >= 1


def test_catalog_sync_is_idempotent(db) -> None:
    sync_permission_catalog(db)
    first = sync_permission_catalog(db)
    assert first["codes_upserted"] == 0


# ── 2. Roles globales (plantillas) ─────────────────────────────────────


def test_global_role_sync_converges_stale_role_to_canonical(db) -> None:
    """El rol global stale (sin check-ins.*) debe quedar alineado al canónico:
    gana check-ins.manage y check-ins.early_approve y pierde cualquier
    divergencia (el $set hace del canónico la fuente de verdad)."""
    _seed_global_role(db, role_name="gerente_hotel", permissions=STALE_GERENTE_GLOBAL_PERMS)

    summary = sync_global_roles(db)

    role = db.roles.find_one({"role_name": "gerente_hotel"})
    stored = set(role["permissions"])
    assert stored == GERENTE_CANONICAL
    assert "check-ins.manage" in stored
    assert "check-ins.early_approve" in stored
    assert summary["roles_modified"] == 1


def test_global_role_sync_is_idempotent(db) -> None:
    _seed_global_role(db, role_name="gerente_hotel", permissions=sorted(GERENTE_CANONICAL))
    second = sync_global_roles(db)
    assert second["roles_modified"] == 0


# ── 3. hotel_roles (clones por hotel — aditivo) ────────────────────────


def test_hotel_role_sync_adds_missing_template_codes_keeping_existing(db) -> None:
    """El clon stale (7 permisos, sin check-ins.*) debe ganar los códigos
    canónicos del template conservando los que ya tenía."""
    template_id = _seed_global_role(
        db, role_name="gerente_hotel", permissions=sorted(GERENTE_CANONICAL)
    )
    _seed_hotel_role(
        db,
        prop_id=1,
        name="gerente_hotel",
        permissions=STALE_GERENTE_HOTEL_ROLE_PERMS,
        based_on_role_id=template_id,
    )

    summary = sync_hotel_roles(db)

    clone = db.hotel_roles.find_one({"prop_id": 1, "name": "gerente_hotel"})
    stored = set(clone["permissions"])
    assert "check-ins.manage" in stored
    assert "check-ins.early_approve" in stored
    # Aditivo: nada de lo que tenía se pierde.
    assert set(STALE_GERENTE_HOTEL_ROLE_PERMS) <= stored
    assert summary["roles_updated"] == 1
    assert summary["codes_added"] >= 2


def test_hotel_role_sync_preserves_custom_extra_codes(db) -> None:
    """Un código custom del hotel que NO está en el template (personalización
    por hotel) debe sobrevivir al sync — el sync es $addToSet, nunca $set."""
    template_id = _seed_global_role(
        db, role_name="gerente_hotel", permissions=sorted(GERENTE_CANONICAL)
    )
    custom = STALE_GERENTE_HOTEL_ROLE_PERMS + ["lost-found.manage"]
    _seed_hotel_role(
        db,
        prop_id=1,
        name="gerente_hotel",
        permissions=custom,
        based_on_role_id=template_id,
    )

    sync_hotel_roles(db)

    clone = db.hotel_roles.find_one({"prop_id": 1, "name": "gerente_hotel"})
    assert "lost-found.manage" in clone["permissions"]
    assert "check-ins.early_approve" in clone["permissions"]


def test_hotel_role_sync_falls_back_to_name_when_no_template(db) -> None:
    """Clones sin based_on_role_id (legacy) se resuelven por nombre de rol."""
    _seed_hotel_role(
        db,
        prop_id=2,
        name="gerente_hotel",
        permissions=STALE_GERENTE_HOTEL_ROLE_PERMS,
        based_on_role_id=None,
    )

    sync_hotel_roles(db)

    clone = db.hotel_roles.find_one({"prop_id": 2, "name": "gerente_hotel"})
    assert "check-ins.early_approve" in clone["permissions"]


def test_hotel_role_sync_is_idempotent(db) -> None:
    template_id = _seed_global_role(
        db, role_name="gerente_hotel", permissions=sorted(GERENTE_CANONICAL)
    )
    _seed_hotel_role(
        db,
        prop_id=1,
        name="gerente_hotel",
        permissions=STALE_GERENTE_HOTEL_ROLE_PERMS,
        based_on_role_id=template_id,
    )
    sync_hotel_roles(db)

    second = sync_hotel_roles(db)
    assert second["roles_updated"] == 0
    assert second["codes_added"] == 0


# ── 3.5 navigation (árbol de navegación — 4ª superficie) ───────────────


def test_navigation_sync_adds_missing_catalog_nodes(db) -> None:
    """Un nodo nuevo del catálogo (p.ej. ``gestion.pms.promociones``) ausente
    en una BD ya seedeada debe aparecer tras el sync, y un nodo legacy
    desactualizado debe converger a los campos canónicos."""
    sync_permission_catalog(db)  # para resolver permission_id
    # Árbol legacy: sin el nodo nuevo y con un nodo stale (label/position viejos).
    db.navigation.insert_one(
        {
            "slug": "gestion.pms.recepcion",
            "label": "Recepción (viejo)",
            "icon": "calendar_month",
            "node_type": "leaf",
            "parent_slug": "gestion.pms",
            "position": 999,
            "permission_code": "reservations.read",
            "href": "/management/recepcion",
            "is_system": True,
        }
    )

    summary = sync_navigation(db)

    stored = {d["slug"] for d in db.navigation.find({}, {"slug": 1})}
    assert NAV_CATALOG_SLUGS <= stored
    assert summary["nodes_upserted"] >= 1
    assert summary["nodes_updated"] >= 1

    recepcion = db.navigation.find_one({"slug": "gestion.pms.recepcion"})
    assert recepcion["label"] != "Recepción (viejo)"
    assert recepcion["position"] != 999
    # FK de permiso resuelta contra la colección permissions sincronizada.
    assert recepcion["permission_id"] is not None


def test_navigation_sync_is_idempotent(db) -> None:
    sync_permission_catalog(db)
    sync_navigation(db)
    before = {
        d["slug"]: d.get("updated_at")
        for d in db.navigation.find({}, {"slug": 1, "updated_at": 1})
    }

    second = sync_navigation(db)

    assert second["nodes_upserted"] == 0
    assert second["nodes_updated"] == 0
    after = {
        d["slug"]: d.get("updated_at")
        for d in db.navigation.find({}, {"slug": 1, "updated_at": 1})
    }
    assert after == before


def test_navigation_sync_reports_orphans_without_deleting(db) -> None:
    sync_permission_catalog(db)
    db.navigation.insert_one(
        {"slug": "custom.hotel.nodo", "label": "Nodo custom", "node_type": "leaf", "is_system": False}
    )

    summary = sync_navigation(db)

    assert "custom.hotel.nodo" in summary["orphans"]
    # Aditivo: el nodo personalizado sobrevive al sync.
    assert db.navigation.find_one({"slug": "custom.hotel.nodo"}) is not None


# ── 4. Escenario end-to-end del incidente ──────────────────────────────


def test_gerente_gains_early_approve_globally_and_hotel_scoped(db) -> None:
    """Tracer bullet del incidente: antes del sync el gerente no puede aprobar
    early check-in ni global ni por hotel; después del sync sí en ambos ejes."""
    from src.app.security.permissions import (
        get_user_permission_codes,
        user_has_permission,
    )

    role_id = _seed_global_role(
        db, role_name="gerente_hotel", permissions=STALE_GERENTE_GLOBAL_PERMS
    )
    user = _seed_gerente_user(db, role_id=role_id)
    clone_id = _seed_hotel_role(
        db,
        prop_id=1,
        name="gerente_hotel",
        permissions=STALE_GERENTE_HOTEL_ROLE_PERMS,
        based_on_role_id=role_id,
    )
    db.role_assignments.insert_one(
        {
            "user_id": user["_id"],
            "prop_id": 1,
            "role_id": clone_id,
            "assigned_by": "test",
            "assigned_at": datetime.now(UTC),
        }
    )

    # ── ANTES: denegado en ambos ejes ──
    assert "check-ins.manage" not in get_user_permission_codes(db, user)
    assert not user_has_permission(db, user, "check-ins.early_approve")
    assert not user_has_permission(db, user, "check-ins.early_approve", prop_id=1)

    summary = sync_all(db)

    # ── DESPUÉS: permitido global y hotel-scoped ──
    global_codes = get_user_permission_codes(db, user)
    assert "check-ins.manage" in global_codes
    assert "check-ins.early_approve" in global_codes
    assert "check-ins.read" in global_codes  # expansión de manage
    assert user_has_permission(db, user, "check-ins.early_approve")
    assert user_has_permission(db, user, "check-ins.early_approve", prop_id=1)
    assert summary["global_roles"]["roles_modified"] >= 1
    assert summary["hotel_roles"]["roles_updated"] >= 1


def test_check_mode_fails_when_dry_run_detects_catalog_delta(db, monkeypatch, capsys) -> None:
    """El modo de guard CI debe fallar sin escribir cuando la BD se aleja del catálogo."""
    monkeypatch.setattr("src.database.connection.get_database", lambda: db)

    exit_code = main(["--dry-run", "--check"])

    assert exit_code == 1
    assert '"delta":' in capsys.readouterr().out
    assert db.permissions.count_documents({}) == 0
    assert db.roles.count_documents({}) == 0
    assert db.hotel_roles.count_documents({}) == 0


def test_check_mode_requires_dry_run() -> None:
    """El guard nunca puede convertirse accidentalmente en una escritura."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--check"])

    assert exc_info.value.code == 2


def test_check_mode_passes_when_catalog_is_aligned(db, monkeypatch, capsys) -> None:
    """El mismo guard devuelve cero cuando no hay cambios pendientes."""
    for role_name, permissions in ROLE_PERMISSION_CODES.items():
        _seed_global_role(db, role_name=role_name, permissions=sorted(permissions))
    sync_all(db)
    monkeypatch.setattr("src.database.connection.get_database", lambda: db)

    exit_code = main(["--dry-run", "--check"])

    assert exit_code == 0
    assert '"delta": 0' in capsys.readouterr().out
