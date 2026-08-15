#!/usr/bin/env python3
"""Repair administrative de folios faltantes para reservas no-show históricas.

Un no-show puede conservar ``stay_status=no_show`` aunque una ejecución
anterior haya fallado antes de insertar su folio. Este script detecta esos
casos y reconstruye únicamente el folio de penalización con el helper
canónico de ``no_show``.

Propiedades de seguridad:

* ``dry-run`` es el modo predeterminado; ``--apply`` es necesario para escribir.
* Nunca elimina ni reescribe reservas, folios existentes o postings.
* No inventa una deuda: un no-show legacy sin
  ``no_show_penalty_amount`` se reporta como omitido.
* Cada folio reparado queda sellado con ``repair_metadata`` y un único evento
  en ``audit_log``.
* Las búsquedas y escrituras se acotan por ``booking_id`` y el folio tiene
  índice único por reserva; repetir la operación no duplica documentos.

Uso dentro del contenedor:

    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/repair_missing_no_show_folios.py --prop-id 1 --dry-run

    docker compose --env-file .env -f infra/docker-compose.yml exec -T server \\
        python scripts/repair_missing_no_show_folios.py --prop-id 1 --apply

El CLI imprime el reporte JSON y, si se pasa ``--report-path``, lo guarda
además en un archivo para revisión/auditoría.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo.errors import PyMongoError

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from src.app.modules.reservations.service.no_show import (
    ensure_no_show_folio,
)
from src.database.connection import get_database

REPAIR_ID = "repair_missing_no_show_folios_v1"
REPAIR_ACTOR = f"system:{REPAIR_ID}"


def utc_now() -> datetime:
    """Return an aware UTC timestamp for repair and audit metadata."""
    return datetime.now(timezone.utc)


def _penalty_amount(booking: dict[str, Any]) -> float | None:
    """Return a persisted penalty amount, or None when evidence is absent."""
    if "no_show_penalty_amount" not in booking:
        return None
    raw = booking.get("no_show_penalty_amount")
    if raw is None:
        return None
    try:
        return round(float(raw), 2)
    except (TypeError, ValueError):
        return None


def _build_query(
    *,
    prop_id: int | None,
    booking_id: str | None,
    check_in_from: str | None,
    check_in_to: str | None,
) -> dict[str, Any]:
    """Build a narrow query for explicit no-show states only."""
    query: dict[str, Any] = {
        "stay_status": "no_show",
        "booking_id": {"$exists": True, "$nin": [None, ""]},
    }
    if prop_id is not None:
        query["prop_id"] = prop_id
    if booking_id:
        query["booking_id"] = booking_id
    if check_in_from or check_in_to:
        date_query: dict[str, str] = {}
        if check_in_from:
            date_query["$gte"] = check_in_from
        if check_in_to:
            date_query["$lte"] = check_in_to
        query["check_in_date"] = date_query
    return query


def _audit_repair(
    db: Any,
    *,
    booking: dict[str, Any],
    folio_number: str,
    amount: float,
    repaired_at: datetime,
) -> None:
    """Write one deduplicated audit event for a repaired folio."""
    booking_id = str(booking["booking_id"])
    existing = db.audit_log.find_one(
        {
            "entity_type": "guest_folio",
            "entity_id": booking_id,
            "action": "repair",
            "metadata.repair_id": REPAIR_ID,
        },
        {"_id": 1},
    )
    if existing:
        return

    db.audit_log.insert_one(
        {
            "timestamp": repaired_at,
            "prop_id": int(booking.get("prop_id", 0) or 0),
            "entity_type": "guest_folio",
            "entity_id": booking_id,
            "action": "repair",
            "summary": f"Reconstrucción de folio no-show {folio_number}",
            "changed_by": REPAIR_ACTOR,
            "diff": {
                "folio_number": {"old": None, "new": folio_number},
                "total_due": {"old": None, "new": amount},
            },
            "metadata": {
                "repair_id": REPAIR_ID,
                "reason": "missing_no_show_folio",
                "source_collection": "booking_orders",
                "source_id": booking_id,
            },
        }
    )


def _stamp_repair_metadata(
    db: Any,
    *,
    booking: dict[str, Any],
    folio_number: str,
    repaired_at: datetime,
) -> None:
    """Stamp the repaired folio without changing financial values."""
    booking_id = str(booking["booking_id"])
    db.guest_folios.update_one(
        {"booking_id": booking_id, "folio_number": folio_number},
        {
            "$set": {
                "repair_metadata.repair_id": REPAIR_ID,
                "repair_metadata.repaired_at": repaired_at,
                "repair_metadata.reason": "missing_no_show_folio",
                "repair_metadata.source_collection": "booking_orders",
                "repair_metadata.source_id": booking_id,
                "updated_at": repaired_at,
            }
        },
    )


def repair_missing_no_show_folios(
    db: Any,
    *,
    dry_run: bool = True,
    prop_id: int | None = None,
    booking_id: str | None = None,
    check_in_from: str | None = None,
    check_in_to: str | None = None,
    limit: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Detect and optionally reconstruct missing no-show folios.

    ``dry_run=True`` is deliberately the default. The returned report is
    deterministic for a fixed database snapshot because candidates are sorted
    by ``booking_id``.
    """
    if limit is not None and limit < 1:
        raise ValueError("limit debe ser mayor que cero")
    if check_in_from and check_in_to and check_in_from > check_in_to:
        raise ValueError("check_in_from no puede ser posterior a check_in_to")

    report: dict[str, Any] = {
        "repair_id": REPAIR_ID,
        "database": getattr(db, "name", None),
        "dry_run": dry_run,
        "filters": {
            "prop_id": prop_id,
            "booking_id": booking_id,
            "check_in_from": check_in_from,
            "check_in_to": check_in_to,
            "limit": limit,
        },
        "scanned": 0,
        "candidates": 0,
        "repaired": 0,
        "already_present": 0,
        "skipped": 0,
        "failed": 0,
        "rows": [],
    }
    repaired_at = now or utc_now()

    cursor = db.booking_orders.find(
        _build_query(
            prop_id=prop_id,
            booking_id=booking_id,
            check_in_from=check_in_from,
            check_in_to=check_in_to,
        ),
        {
            "booking_id": 1,
            "prop_id": 1,
            "guest_name": 1,
            "guest_email": 1,
            "currency": 1,
            "check_in_date": 1,
            "check_out_date": 1,
            "no_show_penalty_amount": 1,
            "no_show_penalty_percent": 1,
        },
    ).sort("booking_id", 1)
    if limit is not None:
        cursor = cursor.limit(limit)

    for booking in cursor:
        report["scanned"] += 1
        current_booking_id = str(booking.get("booking_id") or "")
        existing = db.guest_folios.find_one(
            {"booking_id": current_booking_id},
            {"_id": 1, "folio_number": 1},
        )
        if existing:
            report["already_present"] += 1
            continue

        amount = _penalty_amount(booking)
        if amount is None:
            report["skipped"] += 1
            report["rows"].append(
                {
                    "booking_id": current_booking_id,
                    "prop_id": int(booking.get("prop_id", 0) or 0),
                    "action": "skipped_missing_penalty",
                    "folio_number": None,
                    "penalty_amount": None,
                }
            )
            continue

        report["candidates"] += 1
        row: dict[str, Any] = {
            "booking_id": current_booking_id,
            "prop_id": int(booking.get("prop_id", 0) or 0),
            "action": "would_repair" if dry_run else "repaired",
            "folio_number": None,
            "penalty_amount": amount,
        }
        if not dry_run:
            try:
                folio_number = ensure_no_show_folio(
                    db,
                    booking,
                    penalty_amount=amount,
                    penalty_pct=(
                        int(booking["no_show_penalty_percent"])
                        if booking.get("no_show_penalty_percent") is not None
                        else None
                    ),
                    check_in_str=str(booking.get("check_in_date", ""))[:10],
                    now=repaired_at,
                )
                if not folio_number:
                    raise RuntimeError("el helper no devolvió folio_number")
                _stamp_repair_metadata(
                    db,
                    booking=booking,
                    folio_number=folio_number,
                    repaired_at=repaired_at,
                )
                _audit_repair(
                    db,
                    booking=booking,
                    folio_number=folio_number,
                    amount=amount,
                    repaired_at=repaired_at,
                )
                row["folio_number"] = folio_number
                report["repaired"] += 1
            except (PyMongoError, RuntimeError, TypeError, ValueError) as exc:
                report["failed"] += 1
                row["action"] = "failed"
                row["error"] = str(exc)
        report["rows"].append(row)

    return report


def _default_report_path() -> Path:
    root = Path("/app/data/reports") if Path("/app/data").exists() else Path("data/reports")
    stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
    return root / f"repair_missing_no_show_folios_{stamp}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Solo reporta; es el modo predeterminado.")
    parser.add_argument("--apply", action="store_true", help="Reconstruye los folios faltantes.")
    parser.add_argument("--prop-id", type=int, default=None, help="Limitar a un hotel.")
    parser.add_argument("--booking-id", default=None, help="Limitar a una reserva.")
    parser.add_argument("--check-in-from", default=None, help="Fecha mínima de llegada (YYYY-MM-DD).")
    parser.add_argument("--check-in-to", default=None, help="Fecha máxima de llegada (YYYY-MM-DD).")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de reservas escaneadas.")
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Ruta opcional para guardar el reporte JSON auditable.",
    )
    args = parser.parse_args(argv)
    if args.dry_run and args.apply:
        parser.error("--dry-run y --apply son mutuamente excluyentes")

    db = get_database()
    report = repair_missing_no_show_folios(
        db,
        dry_run=not args.apply,
        prop_id=args.prop_id,
        booking_id=args.booking_id,
        check_in_from=args.check_in_from,
        check_in_to=args.check_in_to,
        limit=args.limit,
    )
    report_path = args.report_path or _default_report_path()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({**report, "report_path": str(report_path)}, indent=2, ensure_ascii=False, default=str))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
