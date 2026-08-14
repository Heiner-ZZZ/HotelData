"""Auditoría read-only de navegación: catálogo canónico (árbol) vs BD dev.

Compara cada nodo del ``NAVIGATION_CATALOG`` (canónico en
``scripts/init_security_model_ga03.py``) contra la colección ``navigation`` de
la BD, en el MODELO ÁRBOL (``slug``/``parent_slug``/``position``/``node_type``/
``permission_code``). Reporta toda desincronización:

1. Nodos canónicos ausentes en la BD (por ``slug``).
2. Nodos en la BD que NO existen en el catálogo canónico (agregados por
   scripts directos sin volver al canónico).
3. Desincronización de campos en nodos compartidos (mismo ``slug``):
   ``parent_slug``, ``position``, ``node_type``, ``permission_code``,
   ``href``, ``label``, ``icon``.
4. ``permission_code`` de navegación que no existe en la colección
   ``permissions`` (un ítem que nunca podrá otorgarse → invisible).
5. Integridad del árbol EN LA BD: huérfanos (``parent_slug`` sin nodo),
   ciclos y ``position`` duplicado por grupo de hermanos.
6. self-FK ``parent_id``: nodos no raíz que no resuelven a su padre.

SOLO LECTURA: no escribe nada en la BD. Por defecto audita la BD dev
(``hoteldata_hub``); usar ``--test`` para la BD de test.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


def _load_canonical_catalog() -> list[dict[str, Any]]:
    """Importa NAVIGATION_CATALOG de init_security_model_ga03.py sin ejecutar main()."""
    spec = importlib.util.spec_from_file_location(
        "init_security_model_ga03_audit",
        SERVER_ROOT / "scripts" / "init_security_model_ga03.py",
    )
    assert spec and spec.loader, "no se pudo cargar init_security_model_ga03.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.NAVIGATION_CATALOG)


_COMPARED_FIELDS = ("parent_slug", "position", "node_type", "permission_code", "href", "label", "icon", "horizontal_menu")


def _fmt(item: dict[str, Any]) -> str:
    return (
        f"  {item.get('slug','?'):<46} parent={item.get('parent_slug')!r:<28} "
        f"pos={item.get('position')!r:<6} type={item.get('node_type')!r:<10} "
        f"perm={item.get('permission_code')!r}".rstrip()
    )


def _find_cycles(by_slug: dict[str, dict[str, Any]]) -> list[list[str]]:
    """Devuelve toda ruta cíclica encontrada en el árbol (por parent_slug)."""
    cycles: list[list[str]] = []
    for start in by_slug:
        path: list[str] = []
        seen: set[str] = set()
        cur: str | None = start
        while cur is not None and cur in by_slug:
            if cur in seen:
                cycles.append(path[path.index(cur):] + [cur])
                break
            seen.add(cur)
            path.append(cur)
            cur = by_slug[cur].get("parent_slug")
    # dedup (rotaciones del mismo ciclo)
    unique: list[list[str]] = []
    for cyc in cycles:
        if not any(set(cyc) == set(u) for u in unique):
            unique.append(cyc)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Auditar la BD de test en vez de dev")
    args = parser.parse_args()

    os.environ["MONGO_DATABASE"] = "hoteldata_hub_test" if args.test else "hoteldata_hub"

    from src.database.connection import get_database

    canonical = _load_canonical_catalog()
    db = get_database()
    db_name = db.name

    db_navs = list(
        db.navigation.find(
            {},
            {"_id": 1, "slug": 1, "parent_slug": 1, "parent_id": 1, "position": 1,
             "node_type": 1, "permission_code": 1, "href": 1, "label": 1, "icon": 1,
             "horizontal_menu": 1},
        )
    )

    canon_by_slug = {item["slug"]: item for item in canonical}
    db_by_slug = {item["slug"]: item for item in db_navs if item.get("slug")}

    print(f"# Auditoría de navegación — BD: {db_name}")
    print(f"Canónico (NAVIGATION_CATALOG): {len(canonical)} nodos · BD (navigation): {len(db_navs)} nodos\n")

    # ── 1. Canónico ausente en BD ──
    missing = [s for s in canon_by_slug if s not in db_by_slug]
    print(f"## 1. Canónico AUSENTE en BD ({len(missing)})")
    for slug in missing:
        print(_fmt(canon_by_slug[slug]))
    if not missing:
        print("  (ninguno)")

    # ── 2. Nodos de BD no canónicos ──
    extras = [s for s in db_by_slug if s not in canon_by_slug]
    print(f"\n## 2. Nodos en BD NO contemplados por el canónico ({len(extras)})")
    for slug in sorted(extras):
        print(_fmt(db_by_slug[slug]))
    if not extras:
        print("  (ninguno)")

    # ── 3. Desincronizaciones por slug compartido ──
    shared = sorted(set(canon_by_slug) & set(db_by_slug))
    diff_fields: list[tuple[str, str, Any, Any]] = []
    for slug in shared:
        c, d = canon_by_slug[slug], db_by_slug[slug]
        for field in _COMPARED_FIELDS:
            cv, dv = c.get(field), d.get(field)
            if cv != dv:
                diff_fields.append((slug, field, cv, dv))
    print(f"\n## 3. Desincronizaciones en nodos compartidos ({len(diff_fields)})")
    for slug, field, cv, dv in diff_fields:
        print(f"  {slug:<46} {field}: canónico={cv!r} → BD={dv!r}")
    if not diff_fields:
        print("  (ninguno)")

    # ── 4. permission_code sin código en el catálogo de permisos ──
    perm_codes = {p.get("permission_code") for p in db.permissions.find({}, {"permission_code": 1})}
    used = sorted({item.get("permission_code") for item in db_navs if item.get("permission_code")})
    orphan = [code for code in used if code not in perm_codes]
    print(f"\n## 4. permission_code de navegación SIN código en `permissions` ({len(orphan)})")
    for code in orphan:
        users = [n["slug"] for n in db_navs if n.get("permission_code") == code]
        print(f"  {code!r} — usado por: {users}")
    if not orphan:
        print("  (todos los códigos existen en el catálogo)")

    # ── 5. Integridad del árbol EN la BD ──
    print("\n## 5. Integridad del árbol en la BD")
    by_slug = {n["slug"]: n for n in db_navs if n.get("slug")}
    orphans = [n["slug"] for n in db_navs if n.get("parent_slug") and n["parent_slug"] not in by_slug]
    cycles = _find_cycles(by_slug)
    groups: dict = defaultdict(list)
    for n in db_navs:
        groups[n.get("parent_slug")].append(n.get("position"))
    dup_positions: dict = {}
    for parent, positions in groups.items():
        dups = sorted({x for x in positions if positions.count(x) > 1})
        if dups:
            dup_positions[parent] = dups
    print(f"  huérfanos={len(orphans)} · ciclos={len(cycles)} · position_duplicado={len(dup_positions)} grupos")
    for slug in orphans:
        print(f"    huérfano: {slug}")
    for cyc in cycles:
        print(f"    ciclo: {' -> '.join(cyc)}")
    for parent, positions in dup_positions.items():
        print(f"    position duplicado en {parent!r}: {positions}")

    # ── 6. self-FK parent_id ──
    print("\n## 6. self-FK parent_id")
    broken_parent: list[str] = []
    for n in db_navs:
        ps = n.get("parent_slug")
        if not ps:
            continue  # raíz: no tiene padre
        parent = by_slug.get(ps)
        if parent is None:
            continue  # ya reportado como huérfano
        pid = n.get("parent_id")
        if pid is None or str(pid) != str(parent.get("_id")):
            broken_parent.append(n["slug"])
    print(f"  parent_id sin resolver/incorrecto: {len(broken_parent)}")
    for slug in broken_parent:
        print(f"    {slug}")

    # ── Resumen ──
    print("\n## Resumen")
    print(f"  canónico={len(canonical)} · BD={len(db_navs)} · ausentes={len(missing)} · "
          f"extras_en_BD={len(extras)} · desync_campos={len(diff_fields)} · "
          f"permisos_huérfanos={len(orphan)} · huérfanos={len(orphans)} · "
          f"ciclos={len(cycles)} · parent_id_rotos={len(broken_parent)}")


if __name__ == "__main__":
    main()
