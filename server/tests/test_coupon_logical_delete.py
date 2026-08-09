"""Borrado lógico de cupones sobrantes al reducir ``coupon_count`` (RF-006).

Contrato que fija este archivo:

- Reducir cupones en ``update_promotion_campaign`` NO borra físicamente:
  los sobrantes sin usar se marcan con ``is_deleted=True`` + ``deleted_at``
  (trazabilidad en ``coupon_codes``).
- Los códigos retirados jamás vuelven a validar en ``validate_coupon_code``
  ni se re-emiten al incrementar (``_generate_coupon_codes`` respeta el
  conjunto de códigos existentes, incluidos los retirados).
- Los conteos operativos (``list_property_campaigns``, ``_coupon_codes_for_prop``,
  KPI de cupones) excluyen retirados; ``coupon_deleted`` expone la traza.
- Un cupón ya usado sigue bloqueando CUALQUIER edición de la campaña y
  jamás se retira.
"""
from __future__ import annotations

import pytest

from src.app.modules.reservations.service.lifecycle.create._validation import (
    validate_coupon_code,
)
from src.app.modules.revenue.services.promotions import (
    create_promotion_campaign,
    list_property_campaigns,
    update_promotion_campaign,
)
from tests.conftest import login

pytestmark = pytest.mark.asyncio

CID = "PC-1-verano"


def _seed_campaign(db) -> None:
    create_promotion_campaign(
        prop_id=1,
        name="Verano",
        description="Verano 2026",
        discount_percent=15,
        start_date="2026-08-01",
        end_date="2026-12-31",
        coupon_count=10,
        is_active=True,
    )


async def test_reduction_marks_surplus_as_logically_deleted(db):
    """Reducir 10→4 conserva los 10 docs: 6 marcados is_deleted + deleted_at."""
    _seed_campaign(db)
    assert db.coupon_codes.count_documents({"campaign_id": CID}) == 10

    update_promotion_campaign(CID, coupon_count=4)

    # Trazabilidad: nada se borró físicamente.
    assert db.coupon_codes.count_documents({"campaign_id": CID}) == 10

    deleted = list(db.coupon_codes.find({"campaign_id": CID, "is_deleted": True}))
    assert len(deleted) == 6
    for doc in deleted:
        assert doc["deleted_at"] is not None
        assert doc["used"] is False

    active = list(db.coupon_codes.find({"campaign_id": CID, "is_deleted": {"$ne": True}}))
    assert len(active) == 4
    assert all("is_deleted" not in c for c in active)

    campaign = db.promotion_campaigns.find_one({"campaign_id": CID})
    assert campaign["coupon_count"] == 4


async def test_retired_coupons_do_not_validate_but_active_still_do(db):
    """Un código retirado ya no valida; uno activo sí (15% + ObjectId FK)."""
    _seed_campaign(db)
    update_promotion_campaign(CID, coupon_count=4)

    retired = db.coupon_codes.find_one({"campaign_id": CID, "is_deleted": True})
    active = db.coupon_codes.find_one({"campaign_id": CID, "is_deleted": {"$ne": True}})

    error, discount, coupon_id = validate_coupon_code(retired["coupon_code"], 1)
    assert error is not None
    assert "no válido" in error.lower()
    assert discount is None
    assert coupon_id is None

    error, discount, coupon_id = validate_coupon_code(active["coupon_code"], 1)
    assert error is None
    assert discount == 15
    assert coupon_id is not None


async def test_increase_after_reduction_generates_new_and_never_reissues_retired(db):
    """10→4→6: total de docs sigue en 10, sin códigos duplicados (ni con retirados)."""
    _seed_campaign(db)

    update_promotion_campaign(CID, coupon_count=4)
    assert db.coupon_codes.count_documents({"campaign_id": CID, "is_deleted": True}) == 6

    update_promotion_campaign(CID, coupon_count=6)

    all_codes = [d["coupon_code"] for d in db.coupon_codes.find({"campaign_id": CID})]
    # 10 iniciales + 2 nuevos = 12; 6 retirados + 6 activos. Sin delete físico.
    assert len(all_codes) == 12
    assert len(all_codes) == len(set(all_codes))  # ningún retirado fue re-emitido

    active = list(db.coupon_codes.find({"campaign_id": CID, "is_deleted": {"$ne": True}}))
    assert len(active) == 6


async def test_operational_counts_exclude_retired(db):
    """coupon_total/used/available reflejan el inventario activo; coupon_deleted la traza."""
    _seed_campaign(db)
    update_promotion_campaign(CID, coupon_count=4)

    result = list_property_campaigns(1)
    campaign = next(c for c in result["campaigns"] if c["campaign_id"] == CID)
    assert campaign["coupon_total"] == 4
    assert campaign["coupon_used"] == 0
    assert campaign["coupon_available"] == 4
    assert campaign["coupon_deleted"] == 6

    # El detalle de tarifas (rates page) solo lista códigos activos.
    from src.app.modules.partner.services.rates.plans import _coupon_codes_for_prop

    codes = _coupon_codes_for_prop(1)
    assert len(codes) == 4
    assert all("is_deleted" not in c for c in codes)


async def test_promotions_api_exposes_coupon_deleted(client, db, admin_user):
    """El wire de GET /api/management/promotions expone la traza de retirados."""
    _seed_campaign(db)
    update_promotion_campaign(CID, coupon_count=4)
    assert await login(client, admin_user["username"], admin_user["password"]) == 200

    resp = await client.get("/api/management/promotions", params={"prop_id": 1})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    campaign = next(c for c in body["campaigns"] if c["campaign_id"] == CID)
    assert campaign["coupon_total"] == 4
    assert campaign["coupon_deleted"] == 6


async def test_repeated_reduce_increase_cycles_keep_bookkeeping_consistent(db):
    """Invariantes tras 10→4→6→3: activo == coupon_count, activo+retirado == docs."""
    _seed_campaign(db)
    update_promotion_campaign(CID, coupon_count=4)  # retira 6
    update_promotion_campaign(CID, coupon_count=6)  # genera 2 nuevos
    update_promotion_campaign(CID, coupon_count=3)  # retira 3 de los 6 activos

    active = list(db.coupon_codes.find({"campaign_id": CID, "is_deleted": {"$ne": True}}))
    deleted = list(db.coupon_codes.find({"campaign_id": CID, "is_deleted": True}))
    all_codes = [d["coupon_code"] for d in db.coupon_codes.find({"campaign_id": CID})]

    assert len(active) == 3
    assert len(deleted) == 9  # 6 + 3, sin delete físico en ningún ciclo
    assert len(all_codes) == 12  # 10 iniciales + 2 nuevos
    assert len(all_codes) == len(set(all_codes))  # ningún retirado re-emitido
    campaign = db.promotion_campaigns.find_one({"campaign_id": CID})
    assert campaign["coupon_count"] == 3


async def test_update_response_reports_coupons_retired(db):
    """La respuesta de update_promotion_campaign reporta cuántos cupones se retiraron."""
    _seed_campaign(db)

    # Reducción 10→4 retira 6 → la respuesta lo expone.
    result = update_promotion_campaign(CID, coupon_count=4)
    assert result["coupons_retired"] == 6

    # Sin reducción (mismo conteo) → 0.
    result = update_promotion_campaign(CID, coupon_count=4)
    assert result["coupons_retired"] == 0

    # Incremento → 0.
    result = update_promotion_campaign(CID, coupon_count=6)
    assert result["coupons_retired"] == 0

    # Edición sin coupon_count (p.ej. solo is_active) → 0.
    result = update_promotion_campaign(CID, is_active=False)
    assert result["coupons_retired"] == 0


async def test_used_coupon_still_blocks_edits_and_is_never_retired(db):
    """Regresión: un cupón usado bloquea la edición y jamás se marca retirado."""
    _seed_campaign(db)
    used = db.coupon_codes.find_one({"campaign_id": CID, "is_deleted": {"$ne": True}})
    db.coupon_codes.update_one({"coupon_code": used["coupon_code"]}, {"$set": {"used": True}})

    with pytest.raises(ValueError, match="utilizado"):
        update_promotion_campaign(CID, coupon_count=4)

    assert db.coupon_codes.count_documents({"campaign_id": CID, "is_deleted": True}) == 0
