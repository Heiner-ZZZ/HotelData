"""Auditoría read-only de navegación: catálogo canónico vs sync vs BD dev.

Compara cada ítem del ``NAVIGATION_CATALOG`` (canónico en
``scripts/init_security_model_ga03.py``) contra la colección ``navigation`` de
la BD y reporta toda desincronización:

1. Ítems canónicos ausentes en la BD.
2. Ítems en la BD que NO existen en el catálogo canónico (agregados por
   ``update_*_navigation.py`` sin volver al canónico).
3. ``required_permission`` distinto entre canónico y BD (mismo href).
4. ``section`` / ``sort_order`` / ``is_section_header`` distintos.
5. ``required_permission`` de navegación que no existe en la colección
   ``permissions`` (un ítem que nunca podrá otorgarse → invisible).

SOLO LECTURA: no escribe nada en la BD. Por defecto audita la BD dev
(``hoteldata_hub``); usar ``--test`` para la BD de test.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
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


def _fmt(item: dict[str, Any]) -> str:
    section = item.get("section") or "-"
    header = "HEADER" if item.get("is_section_header") else ""
    return (
        f"  {item.get('href','?'):<42} perm={item.get('required_permission')!r:<24} "
        f"sort={item.get('sort_order')!r:<7} section={section:<12} {header}".rstrip()
    )


def _norm_is_section_header(value: Any) -> bool:
    """None (canónico omite la clave) y False (BD explícito) son equivalentes."""
    return bool(value)


def _norm_section(value: Any) -> Any:
    """None y clave ausente son equivalentes."""
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Auditar la BD de test en vez de dev")
    args = parser.parse_args()

    if not args.test:
        os.environ["MONGO_DATABASE"] = "hoteldata_hub"
    else:
        os.environ["MONGO_DATABASE"] = "hoteldata_hub_test"

    from src.database.connection import get_database

    canonical = _load_canonical_catalog()
    db = get_database()
    db_name = db.name

    db_navs = list(
        db.navigation.find(
            {},
            {"_id": 0, "label": 1, "href": 1, "required_permission": 1, "section": 1,
             "sort_order": 1, "is_section_header": 1},
        )
    )

    canon_by_href = {item["href"]: item for item in canonical}
    db_by_href = {item["href"]: item for item in db_navs}

    print(f"# Auditoría de navegación — BD: {db_name}")
    print(f"Canónico (NAVIGATION_CATALOG): {len(canonical)} ítems · BD (navigation): {len(db_navs)} ítems\n")

    # ── 1. Canónico ausente en BD ──
    missing = [h for h in canon_by_href if h not in db_by_href]
    print(f"## 1. Canónico AUSENTE en BD ({len(missing)})")
    for href in missing:
        print(_fmt(canon_by_href[href]))
    if not missing:
        print("  (ninguno)")

    # ── 2. Ítems de BD no canónicos ──
    extras = [h for h in db_by_href if h not in canon_by_href]
    print(f"\n## 2. Ítems en BD NO contemplados por el canónico ({len(extras)})")
    for href in sorted(extras, key=lambda h: (db_by_href[h].get("sort_order") or 0, h)):
        print(_fmt(db_by_href[href]))
    if not extras:
        print("  (ninguno)")

    # ── 3-4. Mismatches por href compartido ──
    shared = sorted(set(canon_by_href) & set(db_by_href), key=lambda h: canon_by_href[h].get("sort_order", 0))
    diff_fields = []
    for href in shared:
        c, d = canon_by_href[href], db_by_href[href]
        for field in ("required_permission", "section", "sort_order", "is_section_header"):
            if field == "is_section_header":
                cv, dv = _norm_is_section_header(c.get(field)), _norm_is_section_header(d.get(field))
            elif field == "section":
                cv, dv = _norm_section(c.get(field)), _norm_section(d.get(field))
            else:
                cv, dv = c.get(field), d.get(field)
            if cv != dv:
                diff_fields.append((href, field, cv, dv))
    print(f"\n## 3. Desincronizaciones en ítems compartidos (mismo href, campos distintos) ({len(diff_fields)})")
    for href, field, cv, dv in diff_fields:
        print(f"  {href:<42} {field}: canónico={cv!r} → BD={dv!r}")
    if not diff_fields:
        print("  (ninguno)")

    # ── 5. required_permission sin código en el catálogo de permisos ──
    perm_codes = {p.get("permission_code") for p in db.permissions.find({}, {"permission_code": 1})}
    used = sorted({item.get("required_permission") for item in db_navs if item.get("required_permission")})
    orphan = [code for code in used if code not in perm_codes]
    print(f"\n## 4. required_permission de navegación SIN código en la colección `permissions` ({len(orphan)})")
    for code in orphan:
        print(f"  {code!r} — usado por: {[n['href'] for n in db_navs if n.get('required_permission') == code]}")
    if not orphan:
        print("  (todos los códigos existen en el catálogo)")

    # ── Resumen ──
    print("\n## Resumen")
    print(f"  canónico={len(canonical)} · BD={len(db_navs)} · ausentes={len(missing)} · "
          f"extras_en_BD={len(extras)} · desync_campos={len(diff_fields)} · "
          f"permisos_huérfanos={len(orphan)}")


if __name__ == "__main__":
    main()
