"""Plan the canonical ``category_id`` backfill for legacy guest folio postings.

Legacy ``guest_folios.postings`` entries may store either the human label or
canonical id in ``category`` while omitting ``category_id``. This script reads
those entries and reports the exact embedded postings that *would* receive a
canonical id. It never calls ``update_one``/``bulk_write``/any other write.

The ``--dry-run`` flag is required deliberately so an operator cannot mistake
this read-only planner for an applying migration:

    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
      python scripts/migrate_guest_folios_category_id.py --dry-run

Optional scope:

    ... --dry-run --prop-id 1 --limit 100

The canonical source is ``FOLIO_CATEGORIES`` from the billing folio service;
no category labels or ids are duplicated in this script.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

sys.path.insert(0, "/app")

from pymongo import MongoClient

from config.settings import get_settings
from src.app.modules.billing.service.folio import FOLIO_CATEGORIES

FOLIOS_COLLECTION = "guest_folios"


def normalize_category_key(value: object) -> str:
    """Normalize ids/labels for accent-insensitive, whitespace-safe matching."""
    text = str(value or "").strip()
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.casefold().split())


def build_category_lookup(categories: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """Map both canonical ids and labels to one canonical id.

    Raises ``ValueError`` on an ambiguous normalized key rather than silently
    assigning a legacy posting to the wrong category.
    """
    lookup: dict[str, str] = {}
    for category in categories:
        category_id = str(category.get("id") or "").strip()
        label = str(category.get("label") or "").strip()
        if not category_id:
            continue

        for candidate in (category_id, label):
            key = normalize_category_key(candidate)
            if not key:
                continue
            previous = lookup.get(key)
            if previous is not None and previous != category_id:
                raise ValueError(
                    f"Clave de categoría ambigua {candidate!r}: "
                    f"{previous!r} y {category_id!r}."
                )
            lookup[key] = category_id
    return lookup


def _posting_id(posting: Mapping[str, Any]) -> str:
    value = posting.get("posting_id")
    return str(value) if value is not None else ""


def _posting_summary(posting: Mapping[str, Any]) -> dict[str, str]:
    return {
        "posting_id": _posting_id(posting),
        "category": str(posting.get("category") or ""),
    }


def plan_posting_updates(
    postings: Iterable[Mapping[str, Any]],
    category_lookup: Mapping[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return planned and unmappable posting changes without mutating input."""
    planned: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for posting in postings:
        current_id = posting.get("category_id")
        if current_id is not None and str(current_id).strip():
            continue

        summary = _posting_summary(posting)
        canonical_id = category_lookup.get(normalize_category_key(posting.get("category")))
        if canonical_id is None:
            skipped.append(summary)
            continue

        planned.append({**summary, "category_id": canonical_id})

    return planned, skipped


def scan_guest_folios(
    collection: Any,
    category_lookup: Mapping[str, str],
    *,
    prop_id: int | None = None,
    limit: int = 0,
) -> dict[str, Any]:
    """Scan folios and return a report; this function intentionally performs reads only."""
    query: dict[str, Any] = {"postings": {"$exists": True, "$type": "array"}}
    if prop_id is not None:
        query["prop_id"] = prop_id

    projection = {"booking_id": 1, "prop_id": 1, "postings": 1}
    cursor = collection.find(query, projection)
    if limit > 0:
        cursor = cursor.limit(limit)

    report: dict[str, Any] = {
        "folios_scanned": 0,
        "folios_with_legacy_postings": 0,
        "postings_would_update": 0,
        "postings_skipped": 0,
        "folios": [],
    }

    for folio in cursor:
        report["folios_scanned"] += 1
        planned, skipped = plan_posting_updates(folio.get("postings") or [], category_lookup)
        if not planned and not skipped:
            continue

        report["folios_with_legacy_postings"] += 1
        report["postings_would_update"] += len(planned)
        report["postings_skipped"] += len(skipped)
        report["folios"].append({
            "folio_id": str(folio.get("_id", "")),
            "booking_id": str(folio.get("booking_id") or ""),
            "prop_id": folio.get("prop_id"),
            "planned": planned,
            "skipped": skipped,
        })

    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only dry-run planner for guest_folios.postings.category_id."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Required safety acknowledgement; this script never writes data.",
    )
    parser.add_argument(
        "--skip-seed-source",
        action="store_true",
        help="Compatibility flag; this read-only migration has no seed source to run.",
    )
    parser.add_argument("--prop-id", type=int, default=None, help="Limit the scan to one hotel.")
    parser.add_argument("--limit", type=int, default=0, help="Limit folios scanned; 0 means no limit.")
    args = parser.parse_args(argv)
    if not args.dry_run:
        parser.error("Este script es read-only pero exige la confirmación explícita --dry-run.")
    if args.prop_id is not None and args.prop_id < 1:
        parser.error("--prop-id debe ser mayor que cero.")
    if args.limit < 0:
        parser.error("--limit no puede ser negativo.")
    return args


def _print_report(report: Mapping[str, Any]) -> None:
    print(f"Folios escaneados: {report['folios_scanned']}")
    print(f"Folios con postings legados: {report['folios_with_legacy_postings']}")
    print(f"Postings que recibirían category_id: {report['postings_would_update']}")
    print(f"Postings sin mapeo y omitidos: {report['postings_skipped']}")

    for folio in report["folios"]:
        print(
            f"  Folio {folio['folio_id']} / booking {folio['booking_id']} "
            f"(prop_id={folio['prop_id']})"
        )
        for planned in folio["planned"]:
            print(
                f"    PLAN posting={planned['posting_id']}: "
                f"{planned['category']!r} -> category_id={planned['category_id']!r}"
            )
        for skipped in folio["skipped"]:
            print(
                f"    SKIP posting={skipped['posting_id']}: "
                f"sin categoría canónica para {skipped['category']!r}"
            )

    print("DRY-RUN completo: no se ejecutaron operaciones de escritura.")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = get_settings()
    category_lookup = build_category_lookup(FOLIO_CATEGORIES)

    print(f"Base de datos inspeccionada: {settings.mongo_database}")
    print(f"Categorías canónicas cargadas: {len(FOLIO_CATEGORIES)}")

    client: MongoClient | None = None
    try:
        client = MongoClient(settings.mongo_uri)
        report = scan_guest_folios(
            client[settings.mongo_database][FOLIOS_COLLECTION],
            category_lookup,
            prop_id=args.prop_id,
            limit=args.limit,
        )
        _print_report(report)
        return 0
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
