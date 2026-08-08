"""Invariante: el ``NAVIGATION_CATALOG`` de ``init_security_model_ga03.py`` es
la ÚNICA fuente del menú lateral, y ``seed_navigation()`` la reproduce EXACTA
en la BD (sin faltar, sin sobrar, sin colisiones de ``sort_order``).

Cubre también la regresión de los 5 ítems que vivían solo en la BD dev
(insertados por update_rates_navigation / update_simple_dashboards_navigation /
update_billing_navigation) y fueron back-porteados al catálogo (2026-08) con
sus ``sort_order`` fraccionales — si alguien los borra del catálogo, este test
revienta.

La paridad contra la BD DEV (que sí puede derivar por scripts directos) la
verifica ``server/scripts/_audit_navigation.py``; aquí se comprueba la
invariante reproducible: catálogo → seed → BD exacta en la BD de test.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, SERVER_ROOT / rel)
    assert spec and spec.loader, f"no se pudo cargar {rel}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canon():
    return _load("init_security_model_ga03_nav_audit", "scripts/init_security_model_ga03.py")


# Ítems back-porteados desde la BD dev al NAVIGATION_CATALOG (2026-08).
BACKPORTED = {
    "/management/rates/dashboard": ("Dashboard ADR", "rates.read", "CRS", 204.5),
    "/management/rates/calendar": ("Calendario Tarifas", "rates.read", "CRS", 204.6),
    "/management/service-requests": ("Dashboard Solicitudes", "reservations.read", "CRS", 210.5),
    "/management/billing/dashboard": ("Dashboard", "billing.read", "Billing", 504.5),
    "/management/billing/payments-dashboard": ("Dashboard Pagos", "payments.read", "Billing", 505),
}


def test_catalog_contains_backported_five_items() -> None:
    """Los 5 ítems que antes vivían solo en la BD dev deben estar en el catálogo
    canónico con su label, permiso, sección y sort_order fraccional exactos."""
    canon = _canon()
    by_href = {item["href"]: item for item in canon.NAVIGATION_CATALOG}
    for href, (label, perm, section, sort) in BACKPORTED.items():
        item = by_href.get(href)
        assert item is not None, f"ítem back-porteado {href} NO está en NAVIGATION_CATALOG"
        assert item["label"] == label, f"{href}: label {item['label']!r} != {label!r}"
        assert item["required_permission"] == perm, f"{href}: permiso {item['required_permission']!r} != {perm!r}"
        assert item.get("section") == section, f"{href}: sección {item.get('section')!r} != {section!r}"
        assert item["sort_order"] == sort, f"{href}: sort_order {item['sort_order']!r} != {sort!r}"


def test_catalog_sort_orders_are_unique() -> None:
    """Sin colisiones de sort_order en el catálogo (la colisión 504/505 que
    existía en la BD dev con Pagos/Dashboard billing y Finanzas/Dashboard Pagos)."""
    canon = _canon()
    orders = [item["sort_order"] for item in canon.NAVIGATION_CATALOG]
    dupes = sorted({order for order in orders if orders.count(order) > 1})
    assert not dupes, f"colisión de sort_order en el catálogo: {dupes}"


def test_navigation_required_permissions_exist_in_permission_catalog() -> None:
    """Todo required_permission del menú debe existir en el PERMISSION_CATALOG
    (sin huérfanos que apunten a códigos inexistentes)."""
    canon = _canon()
    perm_codes = {code for code, _ in canon.PERMISSION_CATALOG}
    orphans = sorted(
        {item["required_permission"] for item in canon.NAVIGATION_CATALOG if item.get("required_permission")}
        - perm_codes
    )
    assert not orphans, f"required_permission huérfanos en el catálogo: {orphans}"


def test_seed_navigation_produces_exact_menu_in_test_db() -> None:
    """``seed_navigation()`` sobre una colección vacía de la BD de test deja
    EXACTAMENTE los ítems del catálogo (ni faltan ni sobran) y sin colisiones
    de sort_order — la invariante reproducible de paridad catálogo→BD."""
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
            out = []
            for item in items:
                out.append(
                    {
                        "href": item["href"],
                        "label": item["label"],
                        "required_permission": item.get("required_permission"),
                        "section": item.get("section"),
                        "sort_order": item["sort_order"],
                    }
                )
            return sorted(out, key=lambda item: item["href"])

        assert norm(db_items) == norm(catalog_items), (
            f"el seed no reproduce el catálogo: {len(db_items)} en BD vs {len(catalog_items)} en catálogo"
        )
        orders = [item["sort_order"] for item in db_items]
        dupes = sorted({order for order in orders if orders.count(order) > 1})
        assert not dupes, f"colisión de sort_order tras el seed: {dupes}"
    finally:
        db.client.close()
