"""Índices de ``dim_hotels`` para el gate operativo (published / is_operational).

Design: `docs/APROBACION_HOTELES_Y_PRICING.md` §4. ``published_prop_ids()``
(``server/src/app/modules/hotels/service/operational.py``) se ejecuta en cada
búsqueda pública con ``{"published": {"$ne": False}}`` y proyección
``{"_id": 0, "prop_id": 1}``. Sin índice, eso es un COLLSCAN de toda la
dimensión por búsqueda — inaceptable con miles de hoteles.

Estas pruebas verifican:

1. El bootstrap del módulo hotels crea el índice compuesto
   ``(published, prop_id)`` (cubre exactamente la query+proyección del gate)
   y ``is_operational_1``.
2. ``published_prop_ids`` sigue siendo correcto con estados mixtos
   (publicado / no publicado / legado sin campo).
3. Con miles de hoteles, el plan ganador es un IXSCAN sobre el índice
   compuesto (nunca COLLSCAN) y el número de documentos examinados queda
   acotado por los matches del índice (no escala con el total de la
   colección).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.app.modules.hotels.service.operational import (
    PUBLISHED_QUERY,
    published_prop_ids,
)

pytestmark = pytest.mark.asyncio

PUBLISHED_INDEX = "published_1_prop_id_1"
OPERATIONAL_INDEX = "is_operational_1"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_hotel(db, *, prop_id: int, published=None, is_operational=None) -> None:
    """Seed una fila de dim_hotels. ``published=None`` simula un legado (sin campo)."""
    doc: dict = {
        "prop_id": prop_id,
        "hotel_name": f"Hotel {prop_id}",
        "display_name": f"Hotel {prop_id}",
        "created_at": _now(),
    }
    if published is not None:
        doc["published"] = published
    if is_operational is not None:
        doc["is_operational"] = is_operational
    db.dim_hotels.insert_one(doc)


def _winning_plan(explain: dict) -> dict:
    return explain["queryPlanner"]["winningPlan"]


def _stages(plan: dict) -> list[dict]:
    """Aplana el árbol del winning plan (inputStage / inputStages recursivo)."""
    out: list[dict] = []
    stack = [plan]
    while stack:
        node = stack.pop()
        out.append(node)
        stack.extend(node.get("inputStages") or [])
        child = node.get("inputStage")
        if child:
            stack.append(child)
    return out


def _has_stage(plan: dict, stage: str) -> bool:
    return any(s.get("stage") == stage for s in _stages(plan))


def _index_scans(plan: dict) -> list[str]:
    return [s.get("indexName") for s in _stages(plan) if s.get("stage") == "IXSCAN"]


# ── 1. Bootstrap de índices ──────────────────────────────────────────


async def test_ensure_hotels_collections_creates_published_indexes(db):
    """El bootstrap del módulo hotels crea el índice compuesto (published, prop_id)
    y el de is_operational — verificados tras el arranque del app (conftest)."""
    indexes = db.dim_hotels.index_information()
    assert PUBLISHED_INDEX in indexes, (
        f"Falta el índice compuesto {PUBLISHED_INDEX} en dim_hotels; "
        "ensure_hotels_collections() no está en el lifespan/conftest."
    )
    assert OPERATIONAL_INDEX in indexes, (
        f"Falta el índice {OPERATIONAL_INDEX} en dim_hotels; "
        "ensure_hotels_collections() no está en el lifespan/conftest."
    )


async def test_compound_index_keys_match_query_and_projection_fields(db):
    """El índice compuesto contiene exactamente las claves de la query
    ({published}) y de la proyección ({prop_id}) del gate — precondición
    de un scan eficiente. Solo verifica las claves, no un covered query en
    runtime (eso lo cubre test_published_prop_ids_examined_docs_bounded).

    Nota de divergencia prod/test: la BD real de dim_hotels tiene además
    ``idx_dim_hotels_geo_country`` (migración geo). No contiene ``published``
    ni ``prop_id`` como prefijo, así que nunca puede ganar el plan de esta
    query — el test en la BD de test sigue siendo representativo."""
    keys = list(db.dim_hotels.index_information()[PUBLISHED_INDEX]["key"])
    assert keys == [("published", 1), ("prop_id", 1)]


# ── 2. Correctitud con estados mixtos ────────────────────────────────


async def test_published_prop_ids_mixed_states_correctness(db):
    """published_prop_ids devuelve publicado + legado (sin campo); nunca no publicado."""
    _seed_hotel(db, prop_id=9001, published=True)
    _seed_hotel(db, prop_id=9002, published=False)
    _seed_hotel(db, prop_id=9003)  # legado: sin campo
    _seed_hotel(db, prop_id=9004, published=True, is_operational=True)

    ids = published_prop_ids(db)
    assert sorted(ids) == [9001, 9003, 9004]
    assert 9002 not in ids


# ── 3. Escalado: plan index-backed con miles de hoteles ──────────────


async def test_published_prop_ids_uses_compound_index_at_scale(db):
    """Con 1500 hoteles el plan ganador es un IXSCAN sobre el índice compuesto;
    nunca un COLLSCAN (que degradaría la búsqueda pública a escala)."""
    seeded: list[dict] = []
    for i in range(1, 1501):
        prop_id = 10_000 + i
        if i % 5 == 0:
            doc = {"prop_id": prop_id, "hotel_name": f"H{i}", "display_name": f"H{i}", "published": False}
        elif i % 7 == 0:
            doc = {"prop_id": prop_id, "hotel_name": f"H{i}", "display_name": f"H{i}"}  # legado sin campo
        else:
            doc = {"prop_id": prop_id, "hotel_name": f"H{i}", "display_name": f"H{i}", "published": True}
        doc["created_at"] = _now()
        seeded.append(doc)
    db.dim_hotels.insert_many(seeded)

    ids = published_prop_ids(db)
    expected = {
        d["prop_id"]
        for d in seeded
        if d.get("published") is not False  # publicado explícito + legados
    }
    assert set(ids) == expected

    explain = db.dim_hotels.find(PUBLISHED_QUERY, {"_id": 0, "prop_id": 1}).explain()
    plan = _winning_plan(explain)
    assert not _has_stage(plan, "COLLSCAN"), (
        "published_prop_ids degrada a COLLSCAN con miles de hoteles — "
        "falta el índice compuesto (published, prop_id)."
    )
    assert PUBLISHED_INDEX in _index_scans(plan), (
        f"El plan ganador no usa {PUBLISHED_INDEX}: {plan}"
    )


async def test_published_prop_ids_examined_docs_bounded_at_scale(db):
    """La cantidad de documentos examinados queda acotada por los matches del
    índice — no escala con el total de la colección."""
    for i in range(1, 1501):
        prop_id = 20_000 + i
        published = i % 5 != 0  # 80% publicados
        db.dim_hotels.insert_one(
            {
                "prop_id": prop_id,
                "hotel_name": f"H{i}",
                "display_name": f"H{i}",
                "published": published,
                "created_at": _now(),
            }
        )

    explain = db.command(
        "explain",
        {
            "find": "dim_hotels",
            "filter": PUBLISHED_QUERY,
            "projection": {"_id": 0, "prop_id": 1},
        },
        verbosity="executionStats",
    )
    plan = _winning_plan(explain)
    assert not _has_stage(plan, "COLLSCAN")
    stats = explain["executionStats"]
    assert stats["totalDocsExamined"] < 1500, (
        f"totalDocsExamined={stats['totalDocsExamined']} — el gate examina toda la "
        "colección; el índice compuesto no se está usando."
    )
    # Correctitud a escala: exactamente los 80% publicados (todos con campo).
    ids = published_prop_ids(db)
    assert len(ids) == 1200
