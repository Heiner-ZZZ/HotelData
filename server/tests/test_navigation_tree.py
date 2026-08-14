"""Invariante: ``NAVIGATION_CATALOG`` es un ÁRBOL normalizado (adjacency list
con ``slug``/``parent_slug``/``position``) y cada nodo referencia un código de
permiso EXISTENTE en ``PERMISSION_CATALOG``.

Modelo (2026-08): la navegación deja de ser una lista plana con
``section``/``is_section_header``/``sort_order`` y pasa a un árbol donde
``slug`` es la identidad, ``parent_slug`` la jerarquía (None = raíz/sección),
``position`` el orden local entre hermanos y ``permission_code`` el gate por
nodo. El MISMO árbol alimenta el sidebar vertical y el menú horizontal de
informes.

Invariantes:
1. ``slug`` presente y único en todos los nodos.
2. Todo ``parent_slug`` no nulo referencia un ``slug`` existente (sin huérfanos).
3. Sin ciclos.
4. ``position`` único dentro de cada grupo de hermanos.
5. Todo nodo ``leaf`` tiene ``href``; todo ``container`` tiene hijos.
6. Los dashboards tácticos que antes eran items sueltos cuelgan de un
   container ``Informes`` y usan su código granular propio.
7. Los códigos granulares de informes existen en ``PERMISSION_CATALOG``.
"""

from __future__ import annotations

import importlib.util
from collections import defaultdict
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]


def _canon():
    spec = importlib.util.spec_from_file_location(
        "init_security_model_ga03_tree_audit", SERVER_ROOT / "scripts/init_security_model_ga03.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GRANULAR_REPORT_CODES = {
    "reports.tactical.read",
    "reports.strategic.read",
    "reports.rates.adr.read",
    "reports.rates.calendar.read",
    "reports.requests.read",
    "reports.billing.invoices.read",
    "reports.billing.payments.read",
    "reports.housekeeping.dashboard.read",
    "reports.housekeeping.operations.read",
    "reports.housekeeping.matrix.read",
}

# Dashboards tácticos que antes eran items sueltos y ahora son hojas de un
# container "Informes", cada uno con su código granular.
TACTICAL_REPORT_HREFS = {
    "/management/rates/dashboard": "reports.rates.adr.read",
    "/management/rates/calendar": "reports.rates.calendar.read",
    "/management/service-requests": "reports.requests.read",
    "/management/billing/dashboard": "reports.billing.invoices.read",
    "/management/billing/payments-dashboard": "reports.billing.payments.read",
    "/management/housekeeping/dashboard": "reports.housekeeping.dashboard.read",
    "/management/housekeeping/operations": "reports.housekeeping.operations.read",
    "/management/housekeeping/matrix": "reports.housekeeping.matrix.read",
}


def test_catalog_is_a_well_formed_tree() -> None:
    canon = _canon()
    items = canon.NAVIGATION_CATALOG

    # 1. slug presente y único
    slugs = [item.get("slug") for item in items]
    assert all(slugs), "todo nodo debe tener slug"
    assert len(slugs) == len(set(slugs)), (
        f"slugs duplicados: {sorted({s for s in slugs if slugs.count(s) > 1})}"
    )

    by_slug = {item["slug"]: item for item in items}

    # 2. sin huérfanos
    for item in items:
        parent = item.get("parent_slug")
        if parent is not None:
            assert parent in by_slug, f"huérfano: {item['slug']} → parent_slug {parent!r} inexistente"

    # 3. sin ciclos
    def visit(slug, path):
        if slug in path:
            raise AssertionError(f"ciclo en el árbol: {' -> '.join(path + [slug])}")
        node = by_slug.get(slug)
        if not node:
            return
        parent = node.get("parent_slug")
        if parent is not None:
            visit(parent, path + [slug])

    for item in items:
        visit(item["slug"], [])

    # 4. position único por grupo de hermanos
    groups: dict = defaultdict(list)
    for item in items:
        groups[item.get("parent_slug")].append(item["position"])
    for parent, positions in groups.items():
        assert len(positions) == len(set(positions)), f"position duplicado entre hermanos de {parent!r}"

    # 5. leaf → href; container → tiene hijos
    child_counts: dict = defaultdict(int)
    for item in items:
        if item.get("parent_slug") is not None:
            child_counts[item["parent_slug"]] += 1
    for item in items:
        if item["node_type"] == "leaf":
            assert item.get("href"), f"leaf sin href: {item['slug']}"
        elif item["node_type"] == "container":
            assert child_counts.get(item["slug"], 0) > 0, f"container sin hijos: {item['slug']}"


def test_tactical_dashboards_are_leaves_under_informes_containers() -> None:
    canon = _canon()
    by_slug = {item["slug"]: item for item in canon.NAVIGATION_CATALOG}
    for href, perm in TACTICAL_REPORT_HREFS.items():
        leaf = next((i for i in canon.NAVIGATION_CATALOG if i.get("href") == href), None)
        assert leaf is not None, f"dashboard {href} no está en NAVIGATION_CATALOG"
        assert leaf["node_type"] == "leaf", f"{href} debe ser leaf"
        assert leaf["permission_code"] == perm, f"{href}: permission_code {leaf['permission_code']!r} != {perm!r}"
        parent = by_slug.get(leaf.get("parent_slug"))
        assert parent is not None and parent.get("slug", "").endswith(".informes"), (
            f"{href} debe colgar de un container 'Informes', no de {leaf.get('parent_slug')!r}"
        )


def test_navigation_permission_codes_exist_in_permission_catalog() -> None:
    canon = _canon()
    perm_codes = {code for code, _ in canon.PERMISSION_CATALOG}
    orphans = sorted(
        {item["permission_code"] for item in canon.NAVIGATION_CATALOG if item.get("permission_code")}
        - perm_codes
    )
    assert not orphans, f"permission_code huérfanos en el catálogo: {orphans}"


def test_informes_containers_are_single_links_with_horizontal_menu() -> None:
    """Cada container "Informes" es UN item clickeable en el sidebar: marca
    ``horizontal_menu`` (el sidebar resuelve el destino desde su primer hijo,
    sin duplicar el ``href`` de la hoja — cada ``href`` sigue siendo único)."""
    canon = _canon()
    by_slug = {item["slug"]: item for item in canon.NAVIGATION_CATALOG}

    first_child_href = {
        "gestion.reservas.informes": "/management/rates/dashboard",
        "gestion.housekeeping.informes": "/management/housekeeping/dashboard",
        "gestion.billing.informes": "/management/billing/dashboard",
    }
    for slug, first_href in first_child_href.items():
        node = by_slug[slug]
        assert node["node_type"] == "container", f"{slug} debe seguir siendo container"
        assert node.get("horizontal_menu") is True, f"{slug} debe marcar horizontal_menu"
        assert node.get("href") is None, f"{slug} no debe duplicar el href de su hoja"
        children = [
            i for i in canon.NAVIGATION_CATALOG if i.get("parent_slug") == slug
        ]
        children.sort(key=lambda i: i["position"])
        assert children[0]["href"] == first_href, f"{slug} debe apuntar al primer dashboard {first_href}"


def test_granular_report_permissions_exist() -> None:
    canon = _canon()
    perm_codes = {code for code, _ in canon.PERMISSION_CATALOG}
    missing = sorted(GRANULAR_REPORT_CODES - perm_codes)
    assert not missing, f"faltan códigos granulares de informes en PERMISSION_CATALOG: {missing}"
