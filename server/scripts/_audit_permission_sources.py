"""Auditoría READ-ONLY: seeds/migraciones que definen roles/permisos con listas
propias vs el catálogo canónico (``init_security_model_ga03.py``).

Por cada script candidato reporta:
  - códigos de permiso propios que NO existen en el ``PERMISSION_CATALOG``
    canónico (huérfanos → fuentes divergentes),
  - roles que define y que NO están en ``BASE_ROLES`` canónico,
  - para roles compartidos, la diferencia entre la lista del script y la del
    ``ROLE_PERMISSION_CODES`` canónico (un ``$set`` de un script divergente
    pisaría esas diferencias).

NO escribe nada: solo importa los módulos (todos tienen ``main()`` guardado)
y compara en memoria.

Run: docker compose --env-file .env -f infra/docker-compose.yml exec -T server \
     python -m scripts._audit_permission_sources
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from scripts.init_security_model_ga03 import (  # noqa: E402  (canónico)
    BASE_ROLES,
    PERMISSION_CATALOG,
    ROLE_PERMISSION_CODES,
)

CANON_CODES = {code for code, _ in PERMISSION_CATALOG}
CANON_ROLES = {role_name for role_name, _, _ in BASE_ROLES}

# ── Candidatos: (módulo, extraer_codes, extraer_role_map) ─────────────
# extraer_codes → iterable de códigos propios que el script puede escribir.
# extraer_role_map → dict role_name → list[codes] (o None si solo toca roles).


def _flatten_resource_catalog(catalog) -> list[str]:
    codes = []
    for resource, actions in catalog:
        for action in actions:
            codes.append(f"{resource}.{action}")
    return codes


CANDIDATES = [
    # Escritores $set sobre roles.permissions — los más peligrosos.
    {
        "module": "scripts.sync_role_permissions",
        "kind": "WRITER $set (roles.permissions) + upsert permissions",
        "codes": lambda m: [c for codes in m.ROLE_PERMISSIONS.values() for c in codes],
        "role_map": lambda m: m.ROLE_PERMISSIONS,
    },
    {
        "module": "scripts.add_hotel_staff_roles",
        "kind": "WRITER $set (roles.permissions, upsert de 3 roles)",
        "codes": lambda m: [c for codes in m.ROLE_PERMISSIONS.values() for c in codes],
        "role_map": lambda m: m.ROLE_PERMISSIONS,
    },
    # Catálogo de permisos propio (recurso → acciones).
    {
        "module": "scripts.migrate_permissions_crud",
        "kind": "WRITER upsert permissions (catálogo propio, incl. in-stay.*, charges.create)",
        "codes": lambda m: _flatten_resource_catalog(m.PERMISSION_CATALOG),
        "role_map": None,
    },
    # Backfills $addToSet de un código/recurso puntual.
    {
        "module": "scripts.add_lost_found_permissions",
        "kind": "ADITIVO $addToSet lost-found.*",
        "codes": lambda m: [c for c, _ in m.LOST_FOUND_PERMISSIONS],
        "role_map": lambda m: m.ROLE_LOST_FOUND,
    },
    {
        "module": "scripts.add_reviews_permissions",
        "kind": "ADITIVO $addToSet reviews.*",
        "codes": lambda m: [c for c, _ in m.REVIEWS_PERMISSIONS],
        "role_map": lambda m: m.ROLE_REVIEWS,
    },
    {
        "module": "scripts.add_approve_permission",
        "kind": "ADITIVO $addToSet properties.approve (importa PERMISSION_CATALOG canónico)",
        "codes": lambda m: [m.APPROVE_CODE],
        "role_map": lambda m: {r: [m.APPROVE_CODE] for r in m.APPROVE_HOLDER_ROLES},
    },
    {
        "module": "scripts.add_reviews_read_viewer_roles",
        "kind": "ADITIVO $addToSet reviews.read (roles viewer)",
        "codes": lambda m: [m.REVIEWS_NAV_REQUIRED],
        "role_map": lambda m: {r: [m.REVIEWS_NAV_REQUIRED] for r in m.REVIEW_VIEWER_ROLES},
    },
    {
        "module": "scripts.sync_hotel_manage_roles",
        "kind": "ADITIVO $addToSet hotel.manage_roles (+ hotel_roles)",
        "codes": lambda m: [m.PERMISSION_CODE],
        "role_map": lambda m: {r: [m.PERMISSION_CODE] for r in m.ADMIN_TEMPLATE_ROLES},
    },
]


def main() -> None:
    print(f"Canónico: {len(CANON_CODES)} códigos · {len(CANON_ROLES)} roles (BASE_ROLES)")
    print("=" * 90)
    issues = 0
    for cand in CANDIDATES:
        mod_name = cand["module"]
        try:
            module = importlib.import_module(mod_name)
        except Exception as exc:  # noqa: BLE001 — auditoría, reporta y sigue
            print(f"⚠ {mod_name}: NO importable ({exc})")
            issues += 1
            continue

        own_codes = cand["codes"](module)
        orphan_codes = sorted(set(own_codes) - CANON_CODES)
        role_map = cand["role_map"](module) if cand["role_map"] else None

        print(f"\n◆ {mod_name}")
        print(f"  [{cand['kind']}]")

        if orphan_codes:
            print(f"  🚩 CÓDIGOS HUÉRFANOS (no están en PERMISSION_CATALOG canónico):")
            for code in orphan_codes:
                print(f"     - {code}")
            issues += 1
        else:
            print(f"  ✓ todos los códigos propios existen en el PERMISSION_CATALOG canónico ({len(set(own_codes))})")

        if role_map:
            extra_roles = sorted(set(role_map) - CANON_ROLES)
            if extra_roles:
                print(f"  🚩 ROLES NO CANÓNICOS: {extra_roles}")
                issues += 1
            for role_name, codes in role_map.items():
                if role_name not in CANON_ROLES:
                    continue
                canon = sorted(set(ROLE_PERMISSION_CODES.get(role_name, [])))
                own = sorted(set(codes))
                missing = sorted(set(canon) - set(own))  # canónico que el script no incluye
                extra = sorted(set(own) - set(canon))    # script que canónico no tiene
                if missing or extra:
                    issues += 1
                    print(f"  🚩 {role_name}: difiere del canónico "
                          f"(script={len(own)}, canónico={len(canon)})")
                    if extra:
                        print(f"     + script tiene de más: {extra}")
                    if missing:
                        print(f"     − script NO incluye (lo pisaría un $set): {missing[:12]}{'…' if len(missing) > 12 else ''}")
                else:
                    print(f"  ✓ {role_name}: lista idéntica al canónico ({len(own)})")

    print("\n" + "=" * 90)
    print(f"Total de hallazgos de divergencia: {issues}")


if __name__ == "__main__":
    main()
