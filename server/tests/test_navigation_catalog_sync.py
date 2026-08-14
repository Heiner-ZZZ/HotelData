"""Invariante: ``NAVIGATION_CATALOG`` de ``init_security_model_ga03.py`` es la
ÚNICA fuente del árbol de navegación, y ``seed_navigation()`` lo reproduce
EXACTO en la BD (sin faltar, sin sobrar, sin colisiones de ``position`` por
grupo de hermanos).

La paridad contra la BD DEV (que sí puede derivar por scripts directos) la
verifica ``server/scripts/_audit_navigation.py``; aquí se comprueba la
invariante reproducible: catálogo → seed → BD exacta en la BD de test.
"""

from __future__ import annotations

import importlib.util
import os
from collections import defaultdict
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]


def _canon():
    spec = importlib.util.spec_from_file_location(
        "init_security_model_ga03_nav_audit", SERVER_ROOT / "scripts/init_security_model_ga03.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_navigation_produces_exact_tree_in_test_db() -> None:
    """``seed_navigation()`` sobre una colección vacía deja EXACTAMENTE los
    nodos del catálogo (ni faltan ni sobran) y sin colisiones de ``position``
    por grupo de hermanos — la invariante reproducible de paridad catálogo→BD."""
    from pymongo import MongoClient

    canon = _canon()
    uri = os.environ.get("MONGO_URI", "mongodb://mongo:27018")
    db_name = os.environ.get("MONGO_DATABASE", "hoteldata_hub_test")

    db = MongoClient(uri)[db_name]
    try:
        db.navigation.delete_many({})
        canon.seed_navigation(db["navigation"])

        db_items = list(db.navigation.find({}, {"_id": 0}))
        catalog_items = list(canon.NAVIGATION_CATALOG)

        def norm(items):
            return sorted(
                [
                    {
                        "slug": item["slug"],
                        "parent_slug": item.get("parent_slug"),
                        "position": item["position"],
                        "label": item["label"],
                        "permission_code": item.get("permission_code"),
                        "node_type": item.get("node_type"),
                    }
                    for item in items
                ],
                key=lambda i: i["slug"],
            )

        assert norm(db_items) == norm(catalog_items), (
            f"el seed no reproduce el árbol: {len(db_items)} en BD vs {len(catalog_items)} en catálogo"
        )

        groups: dict = defaultdict(list)
        for item in db_items:
            groups[item.get("parent_slug")].append(item["position"])
        for parent, positions in groups.items():
            assert len(positions) == len(set(positions)), f"colisión de position en {parent!r}"
    finally:
        db.client.close()


def test_seed_navigation_resolves_parent_id_self_fk() -> None:
    """``seed_navigation`` backfillea ``parent_id`` (self-FK ObjectId) en cada
    nodo no raíz apuntando al ``_id`` de su padre; las raíces no llevan FK."""
    from pymongo import MongoClient

    canon = _canon()
    uri = os.environ.get("MONGO_URI", "mongodb://mongo:27018")
    db_name = os.environ.get("MONGO_DATABASE", "hoteldata_hub_test")

    db = MongoClient(uri)[db_name]
    try:
        db.navigation.delete_many({})
        canon.seed_navigation(db["navigation"])

        slug_to_id = {d["slug"]: d["_id"] for d in db.navigation.find({}, {"slug": 1})}

        # raíces (parent_slug None) no deben llevar parent_id
        assert db.navigation.count_documents({"parent_slug": None, "parent_id": {"$exists": True}}) == 0

        broken: list[str] = []
        for doc in db.navigation.find({"parent_slug": {"$ne": None}}):
            pid = doc.get("parent_id")
            if pid is None or pid != slug_to_id.get(doc["parent_slug"]):
                broken.append(doc["slug"])
        assert not broken, f"parent_id sin resolver en: {broken}"
    finally:
        db.client.close()


def test_seed_navigation_resolves_permission_id_when_docs_provided() -> None:
    """Con ``permission_docs`` (código → doc con _id), ``seed_navigation``
    resuelve ``permission_code`` → ``permission_id`` (FK ObjectId) al sembrar."""
    from bson import ObjectId
    from pymongo import MongoClient

    canon = _canon()
    uri = os.environ.get("MONGO_URI", "mongodb://mongo:27018")
    db_name = os.environ.get("MONGO_DATABASE", "hoteldata_hub_test")

    db = MongoClient(uri)[db_name]
    try:
        db.navigation.delete_many({})
        perm_docs = {code: {"_id": ObjectId()} for code, _ in canon.PERMISSION_CATALOG}
        canon.seed_navigation(db["navigation"], perm_docs)

        missing = list(
            db.navigation.find(
                {"permission_code": {"$ne": None}, "permission_id": {"$exists": False}}
            )
        )
        assert not missing, f"nodos sin permission_id resuelto: {len(missing)}"

        adr = db.navigation.find_one({"slug": "gestion.reservas.informes.adr"})
        assert adr is not None
        assert adr["permission_id"] == perm_docs["reports.rates.adr.read"]["_id"]
    finally:
        db.client.close()
