"""Migrate the navigation collection from the flat model to the tree model.

Transforms existing docs (old flat model: ``href``/``required_permission``/
``section``/``is_section_header``/``sort_order``) into the normalized tree
(``slug``/``parent_slug``/``position``/``node_type``/``permission_code``),
adds the new container nodes (raíces, grupos, "Informes"), removes stale docs
and backfills ``parent_id`` (self-FK) + ``permission_id`` (FK → permissions).

Idempotente: correrlo dos veces es un no-op. Apunta a la BD DEV (migración de
restauración), igual que ``migrate_navigation_sections.py`` y
``migrate_navigation_permission_id.py``.

Usage:
  docker compose --env-file .env -f infra/docker-compose.yml exec -T server python scripts/migrate_navigation_tree.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from pymongo import ASCENDING, MongoClient

from config.settings import get_settings
from scripts.init_security_model_ga03 import NAVIGATION_CATALOG, seed_navigation


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[settings.mongo_database]
    nav = db["navigation"]

    # ── 1. Canonical lookup by href (para transformar docs planos viejos) ──
    canonical_by_href: dict[str, dict] = {}
    for node in NAVIGATION_CATALOG:
        if node.get("href"):
            canonical_by_href[node["href"]] = node

    # ── 2. Transformar docs viejos (sin slug) in place ──
    transformed = 0
    stale_ids: list = []
    for doc in nav.find({"slug": {"$exists": False}}):
        href = doc.get("href")
        target = canonical_by_href.get(href)
        if target is None:
            stale_ids.append(doc["_id"])
            continue
        nav.update_one(
            {"_id": doc["_id"]},
            {"$set": {
                "slug": target["slug"],
                "parent_slug": target.get("parent_slug"),
                "position": target.get("position", 0),
                "node_type": target.get("node_type"),
                "permission_code": target.get("permission_code"),
            }},
        )
        transformed += 1

    # ── 3. Borrar docs stale (href ya no está en el árbol canónico) ──
    if stale_ids:
        removed = nav.delete_many({"_id": {"$in": stale_ids}})
        print(f"  ✗ Removed {removed.deleted_count} stale docs (href fuera del árbol canónico)")

    # ── 4. Upsert del árbol canónico completo (añade raíces/containers) ──
    seeded = seed_navigation(nav)
    print(f"  ✓ Transformed {transformed} docs · seeded {seeded} new nodes")

    # ── 5. Backfill parent_id (self-FK ObjectId) ──
    slug_to_id = {doc["slug"]: doc["_id"] for doc in nav.find({"slug": {"$exists": True}}, {"slug": 1})}
    parent_backfilled = 0
    for doc in nav.find({"parent_slug": {"$ne": None}}, {"parent_slug": 1, "parent_id": 1}):
        parent_id = slug_to_id.get(doc.get("parent_slug"))
        if parent_id and doc.get("parent_id") != parent_id:
            nav.update_one({"_id": doc["_id"]}, {"$set": {"parent_id": parent_id}})
            parent_backfilled += 1
    print(f"  ✓ parent_id backfilled: {parent_backfilled}")

    # ── 6. Backfill permission_id (FK → permissions) ──
    code_to_id = {p["permission_code"]: p["_id"] for p in db.permissions.find({}, {"permission_code": 1})}
    perm_backfilled = 0
    for doc in nav.find({"permission_code": {"$ne": None}}, {"permission_code": 1, "permission_id": 1}):
        code = doc.get("permission_code")
        perm_id = code_to_id.get(code) if code else None
        if perm_id and doc.get("permission_id") != perm_id:
            nav.update_one({"_id": doc["_id"]}, {"$set": {"permission_id": perm_id}})
            perm_backfilled += 1
    print(f"  ✓ permission_id backfilled: {perm_backfilled}")

    # ── 7. Índices ──
    nav.create_index("slug", unique=True)
    nav.create_index([("parent_slug", ASCENDING), ("position", ASCENDING)])
    nav.create_index([("permission_id", ASCENDING)], name="idx_nav_permission_id")
    nav.create_index([("parent_id", ASCENDING)], name="idx_nav_parent_id")

    print(f"\n  Total nodes: {nav.count_documents({})}")
    client.close()
    print("\nAll done.")


if __name__ == "__main__":
    main()
