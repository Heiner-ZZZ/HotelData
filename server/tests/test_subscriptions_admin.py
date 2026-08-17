"""Fase 4 — cola de conciliación del admin (PLAN_SUSCRIPCION_Y_PAGOS.md §6.2).

Rutas bajo ``/api/admin/subscriptions``:

- ``GET  /payments``                      → cola de comprobantes (status).
- ``POST /payments/{payment_id}/verify``  → verified + factura paid + sub active.
- ``POST /payments/{payment_id}/reject``  → rejected + sub → pending_payment.
- ``POST /{prop_id}/override``            → precio negociado (price_band_override).
- ``POST /{prop_id}/cancel``              → cancela la suscripción (terminal).

Gates:
- ``require_permission("billing.verify")`` en TODAS las rutas.
- Mutaciones añaden el **gate de supervisor** (``require_supervisor_authorization``):
  solo ``gerente_hotel`` / ``admin_sistema`` / ``super_admin`` pueden conciliar
  dinero o gestionar suscripciones, aunque un rol ad-hoc tuviera el código.
  ``super_admin`` conserva el bypass ``*.*``.
"""

from __future__ import annotations

import pytest
from bson import ObjectId
from passlib.context import CryptContext

from src.app.modules.subscriptions import service as subs

pytestmark = pytest.mark.asyncio

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

VERIFY_PERMISSION = "billing.verify"


# ── Helpers ────────────────────────────────────────────────────────────


def _seed_role(db, *, role_name: str, perms: list[str]) -> ObjectId:
    return db.roles.insert_one(
        {
            "role_name": role_name,
            "display_name": role_name.replace("_", " ").title(),
            "permissions": list(perms),
            "is_system": True,
            "created_at": None,
        }
    ).inserted_id


def _seed_user(
    db,
    *,
    username: str,
    role_name: str,
    password: str = "Pass123!",
    assigned_hotels: list[int] | None = None,
) -> dict:
    doc: dict = {
        "username": username,
        "email": f"{username}@hotel.local",
        "display_name": username.replace("_", " ").title(),
        "password_hash": _pwd.hash(password),
        "primary_role": role_name,
        "is_active": True,
        "created_at": None,
    }
    if assigned_hotels is not None:
        doc["assigned_hotels"] = assigned_hotels
    db.users.insert_one(doc)
    return {"username": username, "password": password}


async def _login(client, username: str, password: str) -> None:
    resp = await client.post(
        "/api/auth/login", json={"identifier": username, "password": password}
    )
    assert resp.status_code == 200, resp.text


async def _login_super_admin(client) -> None:
    await _login(client, "admin_test", "AdminPass123!")


def _seed_subscription_with_payment(
    db, *, prop_id: int = 1, reference: str = "TX-1", amount: float = 89
) -> dict:
    """Suscripción pending + factura + comprobante ``pending_verification``."""
    sub = subs.create_subscription(
        db, prop_id=prop_id, owner_user_id=ObjectId(), band=2, price_usd=89
    )
    db.dim_hotels.insert_one(
        {
            "prop_id": prop_id,
            "hotel_name": f"Hotel {prop_id}",
            "owner_username": f"owner_{prop_id}",
        }
    )
    inv = subs.emit_invoice(db, subscription_id=sub["_id"])
    pay = subs.submit_payment(
        db,
        subscription_id=sub["_id"],
        invoice_id=inv["_id"],
        method="bank_transfer",
        reference=reference,
        amount=amount,
    )
    return {"sub": sub, "inv": inv, "pay": pay}


# ── Gates ──────────────────────────────────────────────────────────────


async def test_payments_requires_auth(client):
    resp = await client.get("/api/admin/subscriptions/payments")
    assert resp.status_code == 401


async def test_payments_forbidden_without_billing_verify(client, db):
    """Usuario sin ``billing.verify`` (recepcionista sin rol sembrado) → 403."""
    _seed_user(db, username="sin_verify", role_name="recepcionista")
    await _login(client, "sin_verify", "Pass123!")

    resp = await client.get("/api/admin/subscriptions/payments")
    assert resp.status_code == 403


async def test_verify_forbidden_for_non_supervisor_role(client, db):
    """Un rol ad-hoc CON ``billing.verify`` pero fuera del allow-list → 403.

    Defensa en profundidad: tener el código no basta — el rol primario debe ser
    supervisor (gerente_hotel / admin_sistema / super_admin).
    """
    _seed_role(db, role_name="recepcionista", perms=[VERIFY_PERMISSION])
    _seed_user(db, username="recepcionista_verify", role_name="recepcionista")
    await _login(client, "recepcionista_verify", "Pass123!")

    seeded = _seed_subscription_with_payment(db)
    resp = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/verify"
    )
    assert resp.status_code == 403
    assert VERIFY_PERMISSION in resp.json()["detail"]


async def test_list_allows_billing_verify_holder_read_only(client, db):
    """La cola (lectura) solo exige el permiso, no el gate de supervisor."""
    _seed_role(db, role_name="recepcionista", perms=[VERIFY_PERMISSION])
    _seed_user(
        db,
        username="recepcionista_verify",
        role_name="recepcionista",
        assigned_hotels=[1],
    )
    await _login(client, "recepcionista_verify", "Pass123!")
    _seed_subscription_with_payment(db)

    resp = await client.get("/api/admin/subscriptions/payments")
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1


async def test_gerente_hotel_with_verify_can_verify(client, db):
    """El supervisor legítimo no-super_admin (gerente_hotel) sí concilia SU hotel."""
    _seed_role(db, role_name="gerente_hotel", perms=[VERIFY_PERMISSION])
    _seed_user(
        db,
        username="gerente_sup",
        role_name="gerente_hotel",
        assigned_hotels=[1],
    )
    await _login(client, "gerente_sup", "Pass123!")
    seeded = _seed_subscription_with_payment(db)

    resp = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/verify"
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == subs.PAYMENT_VERIFIED


# ── GET /payments (cola) ───────────────────────────────────────────────


async def test_payments_list_pending_with_enrichment(client, db, admin_user):
    await _login_super_admin(client)
    seeded = _seed_subscription_with_payment(db, prop_id=7, reference="TX-ENRICH")

    resp = await client.get("/api/admin/subscriptions/payments")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["page"] == 1
    item = body["items"][0]
    assert item["status"] == subs.PAYMENT_PENDING_VERIFICATION
    assert item["reference"] == "TX-ENRICH"
    assert item["method"] == "bank_transfer"
    assert item["amount"] == 89
    assert item["prop_id"] == 7
    assert item["hotel_name"] == "Hotel 7"
    assert item["owner_username"] == "owner_7"
    assert item["id"] == str(seeded["pay"]["_id"])


async def test_payments_list_filters_by_status(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=8, reference="TX-STATUS")

    # Filtrar por un estado sin comprobantes → vacío.
    resp = await client.get(
        "/api/admin/subscriptions/payments", params={"status": subs.PAYMENT_VERIFIED}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0

    # Por defecto y explícito: pending_verification.
    resp = await client.get(
        "/api/admin/subscriptions/payments",
        params={"status": subs.PAYMENT_PENDING_VERIFICATION},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1


# ── Scoping por hotel (plan §6.3) ──────────────────────────────────────


async def test_queue_scoped_to_assigned_hotels_for_restricted_supervisor(client, db):
    """gerente_hotel ve SOLO los comprobantes de su hotel, no la cola cross-hotel."""
    _seed_role(db, role_name="gerente_hotel", perms=[VERIFY_PERMISSION])
    _seed_user(
        db,
        username="gerente_scope",
        role_name="gerente_hotel",
        assigned_hotels=[1],
    )
    await _login(client, "gerente_scope", "Pass123!")
    _seed_subscription_with_payment(db, prop_id=1, reference="OWN")
    _seed_subscription_with_payment(db, prop_id=2, reference="OTHER")

    resp = await client.get("/api/admin/subscriptions/payments")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["prop_id"] == 1
    assert body["items"][0]["reference"] == "OWN"


async def test_queue_empty_for_restricted_supervisor_without_hotels(client, db):
    """Rol restringido sin ``assigned_hotels`` → deny-by-default (no ve nada)."""
    _seed_role(db, role_name="gerente_hotel", perms=[VERIFY_PERMISSION])
    _seed_user(db, username="gerente_no_hotel", role_name="gerente_hotel")
    await _login(client, "gerente_no_hotel", "Pass123!")
    _seed_subscription_with_payment(db, prop_id=1)

    resp = await client.get("/api/admin/subscriptions/payments")
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0


async def test_super_admin_sees_cross_hotel_queue(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=1, reference="A")
    _seed_subscription_with_payment(db, prop_id=2, reference="B")

    resp = await client.get("/api/admin/subscriptions/payments")
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 2


async def test_gerente_hotel_cannot_verify_other_hotel_payment(client, db):
    """El 404 fuera de alcance no debe filtrar existencia ni conciliar el pago."""
    _seed_role(db, role_name="gerente_hotel", perms=[VERIFY_PERMISSION])
    _seed_user(
        db,
        username="gerente_scope",
        role_name="gerente_hotel",
        assigned_hotels=[1],
    )
    await _login(client, "gerente_scope", "Pass123!")
    other = _seed_subscription_with_payment(db, prop_id=2)

    resp = await client.post(
        f"/api/admin/subscriptions/payments/{other['pay']['_id']}/verify"
    )
    assert resp.status_code == 404
    assert (
        db.subscription_payments.find_one({"_id": other["pay"]["_id"]})["status"]
        == subs.PAYMENT_PENDING_VERIFICATION
    )


async def test_gerente_hotel_cannot_override_other_hotel(client, db):
    _seed_role(db, role_name="gerente_hotel", perms=[VERIFY_PERMISSION])
    _seed_user(
        db,
        username="gerente_scope",
        role_name="gerente_hotel",
        assigned_hotels=[1],
    )
    await _login(client, "gerente_scope", "Pass123!")
    _seed_subscription_with_payment(db, prop_id=2)

    resp = await client.post(
        "/api/admin/subscriptions/2/override", json={"price_usd": 55}
    )
    assert resp.status_code == 404


async def test_gerente_hotel_cannot_cancel_other_hotel(client, db):
    _seed_role(db, role_name="gerente_hotel", perms=[VERIFY_PERMISSION])
    _seed_user(
        db,
        username="gerente_scope",
        role_name="gerente_hotel",
        assigned_hotels=[1],
    )
    await _login(client, "gerente_scope", "Pass123!")
    _seed_subscription_with_payment(db, prop_id=2)

    resp = await client.post(
        "/api/admin/subscriptions/2/cancel", json={"reason": "no autorizado"}
    )
    assert resp.status_code == 404


# ── verify ─────────────────────────────────────────────────────────────


async def test_verify_payment_activates_subscription(client, db, admin_user):
    await _login_super_admin(client)
    seeded = _seed_subscription_with_payment(db)

    resp = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/verify"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == subs.PAYMENT_VERIFIED
    assert body["payment_id"] == str(seeded["pay"]["_id"])

    assert (
        db.subscription_payments.find_one({"_id": seeded["pay"]["_id"]})["status"]
        == subs.PAYMENT_VERIFIED
    )
    assert (
        db.subscription_invoices.find_one({"_id": seeded["inv"]["_id"]})["status"]
        == subs.INVOICE_PAID
    )
    assert (
        db.subscriptions.find_one({"prop_id": 1})["status"] == subs.STATUS_ACTIVE
    )


async def test_verify_unknown_payment_404(client, db, admin_user):
    await _login_super_admin(client)
    resp = await client.post(
        f"/api/admin/subscriptions/payments/{ObjectId()}/verify"
    )
    assert resp.status_code == 404


async def test_verify_invalid_payment_id_404(client, db, admin_user):
    await _login_super_admin(client)
    resp = await client.post("/api/admin/subscriptions/payments/no-es-id/verify")
    assert resp.status_code == 404


async def test_verify_double_conflict(client, db, admin_user):
    await _login_super_admin(client)
    seeded = _seed_subscription_with_payment(db)

    first = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/verify"
    )
    assert first.status_code == 200, first.text
    second = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/verify"
    )
    assert second.status_code == 409


# ── reject ─────────────────────────────────────────────────────────────


async def test_reject_payment_returns_to_pending_payment(client, db, admin_user):
    await _login_super_admin(client)
    seeded = _seed_subscription_with_payment(db)

    resp = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/reject",
        json={"reason": "Comprobante ilegible"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == subs.PAYMENT_REJECTED

    pay = db.subscription_payments.find_one({"_id": seeded["pay"]["_id"]})
    assert pay["status"] == subs.PAYMENT_REJECTED
    assert pay["rejection_reason"] == "Comprobante ilegible"
    assert pay["rejected_by"] == "admin_test"
    assert (
        db.subscriptions.find_one({"prop_id": 1})["status"]
        == subs.STATUS_PENDING_PAYMENT
    )


async def test_reject_requires_reason(client, db, admin_user):
    await _login_super_admin(client)
    seeded = _seed_subscription_with_payment(db)

    resp = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/reject",
        json={"reason": "   "},
    )
    assert resp.status_code == 400


async def test_reject_unknown_payment_404(client, db, admin_user):
    await _login_super_admin(client)
    resp = await client.post(
        f"/api/admin/subscriptions/payments/{ObjectId()}/reject",
        json={"reason": "no existe"},
    )
    assert resp.status_code == 404


# ── override ───────────────────────────────────────────────────────────


async def test_override_sets_negotiated_price(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=20)

    resp = await client.post(
        "/api/admin/subscriptions/20/override",
        json={"price_usd": 55, "notes": "Negociado con el dueño"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["price_usd"] == 55
    assert body["price_band_override"] is True

    sub = db.subscriptions.find_one({"prop_id": 20})
    assert sub["price_usd"] == 55
    assert sub["price_band_override"] is True
    assert sub["approval_notes"] == "Negociado con el dueño"
    # La banda derivada se conserva salvo override explícito.
    assert sub["band"] == 2


async def test_override_with_band_updates_band_and_label(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=21)
    db.pricing_plans.insert_one(
        {
            "band": 4,
            "label": "Grande",
            "min_rooms": 51,
            "max_rooms": 300,
            "monthly_usd": 249,
            "annual_monthly_usd": 189,
            "is_active": True,
        }
    )

    resp = await client.post(
        "/api/admin/subscriptions/21/override", json={"price_band": 4}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["band"] == 4
    assert body["band_label"] == "Grande"

    sub = db.subscriptions.find_one({"prop_id": 21})
    assert sub["band"] == 4
    assert sub["band_label"] == "Grande"
    assert sub["price_band_override"] is True


async def test_override_requires_band_or_price(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=22)

    resp = await client.post(
        "/api/admin/subscriptions/22/override", json={"notes": "sin campos"}
    )
    assert resp.status_code == 400


async def test_override_invalid_band_400(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=23)

    resp = await client.post(
        "/api/admin/subscriptions/23/override", json={"price_band": 9}
    )
    assert resp.status_code == 400


async def test_override_unknown_prop_404(client, db, admin_user):
    await _login_super_admin(client)
    resp = await client.post(
        "/api/admin/subscriptions/999/override", json={"price_usd": 50}
    )
    assert resp.status_code == 404


async def test_override_active_schedules_with_preaviso_message(client, db, admin_user):
    """Override sobre suscripción active se programa para el siguiente ciclo."""
    await _login_super_admin(client)
    seeded = _seed_subscription_with_payment(db, prop_id=30)
    verify = await client.post(
        f"/api/admin/subscriptions/payments/{seeded['pay']['_id']}/verify"
    )
    assert verify.status_code == 200, verify.text

    resp = await client.post(
        "/api/admin/subscriptions/30/override",
        json={"price_band": 4, "price_usd": 229, "notes": "Sube a Grande"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "programado" in body["message"].lower()
    assert body["pending_price_band"] == 4
    assert body["pending_price_usd"] == 229
    # Banda y precio actuales sin cambios a mitad de ciclo.
    assert body["band"] == 2
    assert body["price_usd"] == 89

    sub = db.subscriptions.find_one({"prop_id": 30})
    assert sub["band"] == 2
    assert sub["pending_price_band"] == 4
    assert sub["pending_price_usd"] == 229


# ── cancel ─────────────────────────────────────────────────────────────


async def test_cancel_marks_subscription_cancelled(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=30)

    resp = await client.post(
        "/api/admin/subscriptions/30/cancel", json={"reason": "Cierre del hotel"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == subs.STATUS_CANCELLED

    sub = db.subscriptions.find_one({"prop_id": 30})
    assert sub["status"] == subs.STATUS_CANCELLED
    assert sub["cancelled_reason"] == "Cierre del hotel"


async def test_cancel_unknown_prop_404(client, db, admin_user):
    await _login_super_admin(client)
    resp = await client.post(
        "/api/admin/subscriptions/999/cancel", json={"reason": "no existe"}
    )
    assert resp.status_code == 404


async def test_cancel_twice_conflict(client, db, admin_user):
    await _login_super_admin(client)
    _seed_subscription_with_payment(db, prop_id=31)

    first = await client.post(
        "/api/admin/subscriptions/31/cancel", json={"reason": "cierre"}
    )
    assert first.status_code == 200, first.text
    second = await client.post(
        "/api/admin/subscriptions/31/cancel", json={"reason": "otra vez"}
    )
    assert second.status_code == 409


# ── Navegación (sidebar SISTEMA) ────────────────────────────────────────

NAV_SLUG = "sistema.conciliacion-suscripciones"
NAV_HREF = "/admin/subscriptions"


def _nav_node() -> dict | None:
    from scripts.init_security_model_ga03 import NAVIGATION_CATALOG

    return next((n for n in NAVIGATION_CATALOG if n["slug"] == NAV_SLUG), None)


async def test_reconciliation_nav_item_in_catalog():
    """El ítem vive en el catálogo canónico con gate ``billing.verify``."""
    node = _nav_node()
    assert node is not None, "falta el ítem de navegación de conciliación"
    assert node["label"] == "Conciliación de suscripciones"
    assert node["parent_slug"] == "sistema"
    assert node["node_type"] == "leaf"
    assert node["permission_code"] == VERIFY_PERMISSION
    assert node["href"] == NAV_HREF


async def test_reconciliation_nav_seed_resolves_permission_and_visibility(db):
    """``seed_navigation`` persiste el nodo, resuelve ``permission_id`` y lo
    hace visible para quien tiene ``billing.verify``."""
    from scripts.init_security_model_ga03 import seed_navigation
    from src.app.security.navigation import get_all_navigation_items

    inserted = db.permissions.insert_one(
        {
            "permission_code": VERIFY_PERMISSION,
            "description": "Conciliar comprobantes de suscripción",
            "is_system": True,
        }
    )
    perm = db.permissions.find_one({"_id": inserted.inserted_id})
    seed_navigation(db["navigation"], {VERIFY_PERMISSION: perm})

    node = db.navigation.find_one({"slug": NAV_SLUG})
    assert node is not None, "seed_navigation no insertó el ítem de conciliación"
    assert node["permission_code"] == VERIFY_PERMISSION
    assert node["href"] == NAV_HREF
    assert node["permission_id"] == perm["_id"]

    items = get_all_navigation_items({VERIFY_PERMISSION})
    match = next((i for i in items if i["slug"] == NAV_SLUG), None)
    assert match is not None and match["visible"] is True
