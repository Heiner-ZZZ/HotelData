"""Sincronización canónica PBAC: converge una BD a ``init_security_model_ga03.py``.

El catálogo canónico (``PERMISSION_CATALOG`` + ``ROLE_PERMISSION_CODES`` +
``NAVIGATION_CATALOG``) es la única fuente de verdad. Este módulo alinea CUATRO
superficies de una BD existente (dev, staging) sin conocimiento manual del
delta:

1. ``permissions`` — upsert de los códigos del catálogo canónico que faltan en
   la colección (p.ej. ``check-ins.early_approve`` agregado al catálogo en un
   sprint posterior al último seed).
2. ``navigation`` — convergencia del árbol de navegación con
   ``NAVIGATION_CATALOG``: los nodos nuevos del catálogo (p.ej.
   ``gestion.pms.promociones``) aparecen en la BD con sus FKs resueltas
   (``permission_id`` contra ``permissions`` ya sincronizada y ``parent_id``
   self-FK). Los nodos en BD que ya no están en el catálogo se REPORTAN como
   huérfanos pero NO se eliminan (pueden ser nodos personalizados).
3. ``roles`` — ``$set`` del array ``permissions`` con la lista canónica del rol.
   Los templates globales son fuente de verdad canónica: un rol stale gana los
   códigos nuevos y pierde cualquier divergencia (misma semántica que
   ``sync_role_permissions.py``, del que este módulo NO depende para no
   duplicar lógica).
4. ``hotel_roles`` — ``$addToSet`` ADITIVO de los códigos canónicos del
   template que el clon no tiene. Los clones por hotel admiten personalización
   (mismo cargo ≠ mismos permisos en cada hotel — Fase 1 RBAC por hotel), así
   que el sync NUNCA elimina códigos: solo converge hacia arriba lo que el
   template ya otorga. El template se resuelve por ``based_on_role_id`` (FK al
   rol global) y, para clones legacy sin FK, por ``name`` contra el mapa
   canónico.

Idempotente por diseño: una segunda pasada no modifica ningún documento
(``modified_count == 0``). Acepta ``--dry-run`` para reportar sin escribir.

Uso (dentro del contenedor server, apunta a la BD de la env var):
    python -m scripts.sync_pbac_permissions [--dry-run]
    python -m scripts.sync_pbac_permissions --dry-run --check

``--check`` exige ``--dry-run`` y devuelve código distinto de cero cuando la
corrida detectaría cualquier cambio canónico. Los nodos de navegación huérfanos
no cuentan como delta porque pueden ser personalizaciones legítimas; se siguen
reportando sin eliminar.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from scripts.init_security_model_ga03 import (
    NAVIGATION_CATALOG,
    PERMISSION_CATALOG,
    ROLE_PERMISSION_CODES,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


# ── 1. Catálogo de permisos ────────────────────────────────────────────


def sync_permission_catalog(db: Any, *, dry_run: bool = False) -> dict[str, Any]:
    """Upsert de ``PERMISSION_CATALOG`` canónico en ``permissions``.

    Reporta cuántos códigos faltaban (los únicos que el upsert realmente crea).
    Re-ejecutar es un no-op (``codes_upserted == 0``).
    """
    now = utc_now()
    existing = {
        p["permission_code"]
        for p in db.permissions.find({}, {"permission_code": 1})
    }
    missing = [code for code, _ in PERMISSION_CATALOG if code not in existing]

    if not dry_run:
        for code, description in PERMISSION_CATALOG:
            db.permissions.update_one(
                {"permission_code": code},
                {
                    "$set": {
                        "permission_code": code,
                        "description": description,
                        "is_system": True,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )

    return {
        "codes_total": len(PERMISSION_CATALOG),
        "codes_upserted": len(missing),
        "dry_run": dry_run,
    }


# ── 2. Roles globales (plantillas) ─────────────────────────────────────


def sync_global_roles(
    db: Any,
    *,
    dry_run: bool = False,
    role_names: list[str] | None = None,
) -> dict[str, Any]:
    """``$set`` del array canónico en cada rol global gestionado.

    El template global es fuente de verdad: el ``$set`` alinea el rol stale con
    ``ROLE_PERMISSION_CODES`` (suma códigos nuevos, elimina divergencias).
    """
    now = utc_now()
    targets = role_names or list(ROLE_PERMISSION_CODES)
    matched = 0
    modified = 0
    missing_roles: list[str] = []

    for role_name in targets:
        canon = ROLE_PERMISSION_CODES.get(role_name)
        if canon is None:
            continue
        role = db.roles.find_one({"role_name": role_name}, {"_id": 1, "permissions": 1})
        if role is None:
            missing_roles.append(role_name)
            continue
        matched += 1
        # Solo escribe cuando el array realmente diverge del canónico: una
        # segunda pasada (idempotencia) no debe tocar el documento ni churnear
        # ``updated_at`` (un ``$set`` incondicional de timestamp haría que
        # ``modified_count`` fuera 1 en cada re-ejecución).
        if set(role.get("permissions", [])) == set(canon):
            continue
        modified += 1
        if dry_run:
            continue
        db.roles.update_one(
            {"_id": role["_id"]},
            {"$set": {"permissions": list(canon), "updated_at": now}},
        )

    return {
        "roles_matched": matched,
        "roles_modified": modified,
        "roles_missing": missing_roles,
        "dry_run": dry_run,
    }


# ── 3. navigation (árbol de navegación — 4ª superficie) ────────────────

# Campos del nodo que el sync mantiene alineados con NAVIGATION_CATALOG.
_NAV_FIELDS = ("label", "icon", "node_type", "parent_slug", "position", "permission_code", "href")


def _nav_changed_fields(existing: dict[str, Any], catalog_item: dict[str, Any]) -> list[str]:
    """Campos del nodo existente que divergen del ítem canónico."""
    changed = [f for f in _NAV_FIELDS if existing.get(f) != catalog_item.get(f)]
    if existing.get("is_system") is not True:
        changed.append("is_system")
    return changed


def sync_navigation(db: Any, *, dry_run: bool = False) -> dict[str, Any]:
    """Converge la colección ``navigation`` con ``NAVIGATION_CATALOG``.

    El middleware filtra el sidebar por la colección ``navigation`` (cada nodo
    lleva ``permission_code``), así que sin esta superficie un nodo nuevo del
    catálogo nunca aparece en una BD ya seedeada aunque los roles estén
    alineados — el hueco que dejaba el sync de 3 superficies.

    Semántica: upsert por ``slug`` con DIFF — una segunda pasada no escribe
    nada (mismo contrato de idempotencia que ``roles``). Resuelve
    ``permission_id`` contra la colección ``permissions`` (que la superficie 1
    acaba de sincronizar) y ``parent_id`` (self-FK) tras el upsert. Los nodos
    en BD que ya no están en el catálogo se REPORTAN como huérfanos pero NO se
    eliminan: pueden ser nodos personalizados (filosofía aditiva de
    ``hotel_roles``).
    """
    now = utc_now()
    perm_ids = {
        p["permission_code"]: p["_id"]
        for p in db.permissions.find({}, {"permission_code": 1})
        if p.get("permission_code")
    }

    nodes_total = len(NAVIGATION_CATALOG)
    nodes_upserted = 0
    nodes_updated = 0

    for item in NAVIGATION_CATALOG:
        slug = item["slug"]
        existing = db.navigation.find_one({"slug": slug})

        if existing is None:
            nodes_upserted += 1
            if dry_run:
                continue
            doc: dict[str, Any] = {
                **{f: item.get(f) for f in _NAV_FIELDS},
                "slug": slug,
                "is_system": True,
                "created_at": now,
                "updated_at": now,
            }
            code = item.get("permission_code")
            if code and code in perm_ids:
                doc["permission_id"] = perm_ids[code]
            db.navigation.insert_one(doc)
            continue

        changed = _nav_changed_fields(existing, item)
        code = item.get("permission_code")
        perm_id_ok = (not code) or (
            code in perm_ids and existing.get("permission_id") == perm_ids[code]
        )
        if not changed and perm_id_ok:
            continue
        nodes_updated += 1
        if dry_run:
            continue
        set_fields: dict[str, Any] = {f: item.get(f) for f in changed} if changed else {}
        set_fields["is_system"] = True
        set_fields["updated_at"] = now
        if code and code in perm_ids:
            set_fields["permission_id"] = perm_ids[code]
        db.navigation.update_one({"_id": existing["_id"]}, {"$set": set_fields})

    # parent_id (self-FK) tras el upsert: el padre ya existe en BD.
    if not dry_run:
        slug_to_id = {
            d["slug"]: d["_id"]
            for d in db.navigation.find({"slug": {"$exists": True}}, {"slug": 1})
        }
        for item in NAVIGATION_CATALOG:
            parent_slug = item.get("parent_slug")
            if not parent_slug:
                continue
            parent_id = slug_to_id.get(parent_slug)
            if parent_id is None:
                continue
            db.navigation.update_one(
                {"slug": item["slug"], "parent_id": {"$ne": parent_id}},
                {"$set": {"parent_id": parent_id}},
            )

    db_slugs = {
        d["slug"] for d in db.navigation.find({}, {"slug": 1}) if d.get("slug")
    }
    catalog_slugs = {item["slug"] for item in NAVIGATION_CATALOG}
    orphans = sorted(db_slugs - catalog_slugs)

    return {
        "nodes_total": nodes_total,
        "nodes_upserted": nodes_upserted,
        "nodes_updated": nodes_updated,
        "orphans": orphans,
        "dry_run": dry_run,
    }


# ── 4. hotel_roles (clones por hotel — aditivo) ────────────────────────


def _coerce_object_id(value: Any) -> ObjectId | None:
    if isinstance(value, ObjectId):
        return value
    if isinstance(value, str):
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None
    return None


def _canonical_codes_for_hotel_role(
    db: Any,
    hotel_role: dict[str, Any],
) -> list[str] | None:
    """Resuelve los códigos canónicos que el template otorga a este clon.

    Prefiere la FK ``based_on_role_id`` → rol global → ``role_name``; para
    clones legacy sin FK (o con FK rota) cae al ``name`` del clon contra el
    mapa canónico. Sin match → ``None`` (el clon no se toca).
    """
    role_name: str | None = None
    based_on = _coerce_object_id(hotel_role.get("based_on_role_id"))
    if based_on is not None:
        template = db.roles.find_one({"_id": based_on}, {"role_name": 1})
        if template and template.get("role_name"):
            role_name = template["role_name"]
    if role_name is None:
        role_name = (hotel_role.get("name") or "").strip() or None
    if role_name is None:
        return None
    return ROLE_PERMISSION_CODES.get(role_name)


def sync_hotel_roles(db: Any, *, dry_run: bool = False) -> dict[str, Any]:
    """Converge los clones de ``hotel_roles`` con su template canónico.

    Aditivo por diseño: ``$addToSet`` de los códigos del template que faltan.
    Nunca elimina códigos (la personalización por hotel es parte del modelo) y
    nunca toca clones cuyo nombre/FK no resuelve a un rol canónico.
    """
    now = utc_now()
    roles_total = 0
    roles_updated = 0
    codes_added = 0
    roles_skipped = 0

    for hotel_role in db.hotel_roles.find(
        {},
        {"_id": 1, "name": 1, "based_on_role_id": 1, "permissions": 1},
    ):
        roles_total += 1
        canon = _canonical_codes_for_hotel_role(db, hotel_role)
        if canon is None:
            roles_skipped += 1
            continue
        current = set(hotel_role.get("permissions", []))
        missing = sorted(set(canon) - current)
        if not missing:
            continue
        roles_updated += 1
        codes_added += len(missing)
        if dry_run:
            continue
        db.hotel_roles.update_one(
            {"_id": hotel_role["_id"]},
            {
                "$addToSet": {"permissions": {"$each": missing}},
                "$set": {"updated_at": now},
            },
        )

    return {
        "roles_total": roles_total,
        "roles_updated": roles_updated,
        "codes_added": codes_added,
        "roles_skipped": roles_skipped,
        "dry_run": dry_run,
    }


# ── 5. One-shot ────────────────────────────────────────────────────────


def sync_all(db: Any, *, dry_run: bool = False) -> dict[str, Any]:
    """Aplica las cuatro superficies en orden: catálogo → navigation (necesita
    los ``_id`` de permissions) → roles → hotel_roles."""
    return {
        "catalog": sync_permission_catalog(db, dry_run=dry_run),
        "navigation": sync_navigation(db, dry_run=dry_run),
        "global_roles": sync_global_roles(db, dry_run=dry_run),
        "hotel_roles": sync_hotel_roles(db, dry_run=dry_run),
        "dry_run": dry_run,
    }


def calculate_sync_delta(summary: dict[str, Any]) -> int:
    """Cuenta cambios que el sync aplicaría a las superficies canónicas.

    El delta es deliberadamente conservador: cualquier código/documento que el
    sync pueda crear, actualizar o completar hace fallar ``--check``. Los
    ``navigation.orphans`` quedan fuera porque el contrato del sync los trata
    como nodos personalizados reportables, no como stale drift.
    """
    catalog = summary.get("catalog", {})
    navigation = summary.get("navigation", {})
    global_roles = summary.get("global_roles", {})
    hotel_roles = summary.get("hotel_roles", {})

    return sum(
        (
            int(catalog.get("codes_upserted", 0)),
            int(navigation.get("nodes_upserted", 0)),
            int(navigation.get("nodes_updated", 0)),
            int(global_roles.get("roles_modified", 0)),
            len(global_roles.get("roles_missing", [])),
            int(hotel_roles.get("codes_added", 0)),
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sincroniza el catálogo PBAC canónico en la BD actual: "
            "permissions (upsert) + navigation (árbol) + roles ($set) + "
            "hotel_roles ($addToSet aditivo)."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reporta lo que haría sin escribir nada.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Falla si el dry-run detecta delta; exige --dry-run y es apto para CI."
        ),
    )
    args = parser.parse_args(argv)
    if args.check and not args.dry_run:
        parser.error("--check requiere --dry-run para impedir escrituras accidentales.")

    from src.database.connection import get_database

    db = get_database()
    summary = sync_all(db, dry_run=args.dry_run)
    delta = calculate_sync_delta(summary)
    summary["delta"] = delta
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    action = "Would apply" if args.dry_run else "Applied"
    nav = summary["navigation"]
    print(
        f"{action}: delta={delta}, catalog={summary['catalog']['codes_upserted']} code(s), "
        f"navigation={nav['nodes_upserted']} new + {nav['nodes_updated']} updated "
        f"({len(nav['orphans'])} orphan(s) reported), "
        f"global_roles={summary['global_roles']['roles_modified']} modified, "
        f"hotel_roles={summary['hotel_roles']['roles_updated']} updated "
        f"({summary['hotel_roles']['codes_added']} code(s))"
    )
    if args.check and delta != 0:
        print(
            f"CHECK FAILED: el catálogo PBAC tiene delta={delta}; "
            "ejecuta el sync sin --check para converger la BD.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
