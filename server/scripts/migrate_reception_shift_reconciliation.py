"""Reconcile historical cash-required actions with reception shifts.

This migration is intentionally conservative and non-destructive:

* Existing reservations, payments, folios, and shifts are never deleted.
* The one reviewed cash payment and five reviewed completed check-outs get
  closed morning/afternoon/evening shifts for their UTC date buckets when one
  does not already exist, then receive that shift's ObjectId FK.
* Horuz's reviewed folio is linked only to the exact existing historical
  shift ``6a763298f1b31b5a7a98e00e``.
* Web/customer bookings are never assigned from creation alone; the five
  reviewed completed check-outs are the explicit exception.
* Existing stale ``booking_ids`` in a shift are removed only from the summary
  array when the booking is web-channel, missing, or points to another shift;
  the original array is preserved under ``reconciliation.original_refs``.
* Probable smoke/demo shifts are marked, not deleted.
* Every mutation is stamped with ``metadata.migration_id`` and mirrored in
  ``audit_log``. A JSON report is written under ``data/reports``.

Dry-run is the default. Apply only after reviewing the report:

    python scripts/migrate_reception_shift_reconciliation.py --prop-id 1
    python scripts/migrate_reception_shift_reconciliation.py --prop-id 1 --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import ObjectId  # noqa: E402

from src.database.connection import get_database  # noqa: E402

MIGRATION_ID = "reconcile_reception_shifts_2026_08"
RECEPTION_SHIFTS = "reception_shifts"
WEB_CHANNEL_SOURCES = frozenset(
    {
        "web_request",
        "web",
        "booking_engine",
        "direct",
        "direct_website",
        "ota",
        "booking.com",
        "expedia",
        "cliente",
    }
)

# Minutes from midnight UTC. ``evening`` is 00:00–08:00 because the existing
# project shift model uses that bucket for the overnight window.
BUCKETS: dict[str, tuple[int, int]] = {
    "morning": (8 * 60, 16 * 60),
    "afternoon": (16 * 60, 24 * 60),
    "evening": (0, 8 * 60),
}

PROBABLE_DEMO_EMPLOYEES = frozenset(
    {"Recepcionista Prueba", "Recepcionista UI Test", "Super Admin Demo"}
)

# Reviewed evidence from the read-only audit. Keep this allowlist explicit:
# the migration must not infer cashier activity from generic historical rows.
APPROVED_CASH_PAYMENT_IDS = frozenset({"6a5be0362b365ae1d36f6f7a"})
APPROVED_CHECKOUT_TIMESTAMPS = {
    "BK-20260630012717-DC5DF649": "2026-07-01T03:43:00+00:00",
    "BK-20260630060318-C76A2F39": "2026-07-02T03:21:00+00:00",
    "BK-20260701032655-8F726DCE": "2026-07-04T20:18:00+00:00",
    "BK-20260701033656-FD7049F6": "2026-08-01T03:09:00+00:00",
    "BK-20260704164045-6992E4A7": "2026-07-05T15:14:00+00:00",
}
HORUZ_BOOKING_ID = "BK-20260709132144-89DA890A"
HORUZ_SHIFT_ID = "6a763298f1b31b5a7a98e00e"
HORUZ_CHECKOUT_DATE = "2026-08-07"
APPROVED_HORUZ_FOLIO_ID = "6a4fa390582bc64092e388a3"

# These five folios were reviewed and deliberately rejected as cash evidence:
# they are closed web folios, not proof that reception handled cash.
EXCLUDED_WEB_FOLIO_IDS = frozenset(
    {
        "6a431c58484c641cb4a3fdc2",
        "6a435c4c082f35d04ed4ffe5",
        "6a448957609c2072fc72f5c6",
        "6a44a11527aecd34de08431d",
        "6a4941bd9a90edff434c7663",
    }
)


def parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def bucket_for_datetime(value: datetime) -> str:
    """Return the project cash bucket for a timezone-aware datetime."""
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    minutes = dt.hour * 60 + dt.minute
    if minutes < BUCKETS["morning"][0]:
        return "evening"
    if minutes < BUCKETS["afternoon"][0]:
        return "morning"
    return "afternoon"


def bucket_window(value: datetime, bucket: str) -> tuple[datetime, datetime]:
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    start_minute, end_minute = BUCKETS[bucket]
    day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    start = day + timedelta(minutes=start_minute)
    end = day + timedelta(minutes=end_minute) - timedelta(microseconds=1)
    return start, end


def is_cash_payment(doc: dict[str, Any]) -> bool:
    """Return whether a payment has the generic physical-cash shape."""
    method = str(doc.get("method") or "").strip().lower()
    status = str(doc.get("status") or "").strip().lower()
    return method in {"cash", "efectivo"} and status in {"confirmed", "refunded"}


def is_approved_historical_payment(doc: dict[str, Any]) -> bool:
    """Accept only the one payment confirmed by the reviewed dry-run."""
    return (
        safe(doc.get("_id")) in APPROVED_CASH_PAYMENT_IDS
        and str(doc.get("booking_id") or "") == HORUZ_BOOKING_ID
        and is_cash_payment(doc)
        and round(float(doc.get("amount") or 0), 2) == 1.00
        and (
            (parse_timestamp(doc.get("paid_at") or doc.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)).replace(second=0, microsecond=0)
            == datetime(2026, 7, 18, 20, 21, tzinfo=timezone.utc)
        )
    )


def is_approved_historical_checkout(doc: dict[str, Any]) -> bool:
    """Accept only the five reviewed completed check-outs."""
    booking_id = str(doc.get("booking_id") or "")
    actual = checkout_timestamp(doc)
    expected = parse_timestamp(APPROVED_CHECKOUT_TIMESTAMPS.get(booking_id))
    return (
        booking_id in APPROVED_CHECKOUT_TIMESTAMPS
        and is_checkout_evidence(doc)
        and actual is not None
        and actual == expected
    )


def is_approved_historical_folio(doc: dict[str, Any]) -> bool:
    """Accept only Horuz's folio, which must reuse its existing shift."""
    folio_id = safe(doc.get("_id"))
    return folio_id == APPROVED_HORUZ_FOLIO_ID and folio_id not in EXCLUDED_WEB_FOLIO_IDS


def is_checkout_evidence(doc: dict[str, Any]) -> bool:
    """Identify an actual completed checkout from booking state fields."""
    return bool(
        doc.get("stay_status") == "checked_out"
        and doc.get("check_out_date_actual")
    )


def checkout_timestamp(doc: dict[str, Any]) -> datetime | None:
    """Combine the actual checkout date/time fields into a UTC datetime."""
    date_value = str(doc.get("check_out_date_actual") or "").strip()
    time_value = str(doc.get("check_out_time_actual") or "00:00").strip()
    if not date_value:
        return None
    try:
        value = datetime.fromisoformat(f"{date_value}T{time_value}")
    except ValueError:
        return None
    return value.replace(tzinfo=timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def safe(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [safe(item) for item in value]
    if isinstance(value, dict):
        return {key: safe(item) for key, item in value.items()}
    return value


def shift_signature(doc: dict[str, Any]) -> tuple[int, str, str] | None:
    start = parse_timestamp(doc.get("start_time"))
    if start is None or not doc.get("prop_id") or doc.get("shift_type") not in BUCKETS:
        return None
    return int(doc["prop_id"]), start.date().isoformat(), str(doc["shift_type"])


def probable_demo(doc: dict[str, Any]) -> bool:
    """Mark only an explicit demo/test actor label.

    ``closing_notes`` is intentionally excluded: Carlos Mendoza has a real
    employee name and a note saying ``Prueba flujo real API``, which is not
    enough evidence to classify the shift as synthetic.
    """
    return str(doc.get("employee") or "").strip() in PROBABLE_DEMO_EMPLOYEES


def _action_events(db: Any, prop_id: int) -> list[dict[str, Any]]:
    """Return only evidence that can justify a historical cash shift.

    Only the reviewed physical-cash payment, reviewed completed check-outs,
    and Horuz's reviewed folio are emitted. Generic booking creation and
    closed web folios are intentionally excluded.
    """
    events: list[dict[str, Any]] = []
    for doc in db.reservation_payments.find({"prop_id": prop_id}):
        # The reviewed dry-run identified exactly one physical-cash movement.
        # Do not generalize from method/status: simulated, card, failed, and
        # other historical payments are intentionally left untouched.
        if not is_approved_historical_payment(doc):
            continue
        ts = parse_timestamp(doc.get("paid_at") or doc.get("created_at"))
        if ts:
            events.append({"kind": "payment", "timestamp": ts, "doc": doc})

    for doc in db.guest_folios.find({"prop_id": prop_id}):
        # Only Horuz's folio is approved. Its event timestamp is the actual
        # checkout timestamp so it resolves to the existing 2026-08-07
        # morning shift, never to a newly-created afternoon shift.
        if not is_approved_historical_folio(doc):
            continue
        booking = db.booking_orders.find_one(
            {"booking_id": HORUZ_BOOKING_ID},
            {
                "booking_id": 1,
                "shift_id": 1,
                "stay_status": 1,
                "check_out_date_actual": 1,
                "check_out_time_actual": 1,
            },
        )
        ts = checkout_timestamp(booking or {})
        if (
            booking
            and booking.get("booking_id") == HORUZ_BOOKING_ID
            and booking.get("stay_status") == "checked_out"
            and str(booking.get("shift_id")) == HORUZ_SHIFT_ID
            and ts is not None
            and ts.date().isoformat() == HORUZ_CHECKOUT_DATE
        ):
            events.append(
                {
                    "kind": "folio",
                    "timestamp": ts,
                    "doc": doc,
                    "requires_existing_shift": True,
                    "preferred_shift_id": HORUZ_SHIFT_ID,
                }
            )

    for doc in db.booking_orders.find({"prop_id": prop_id}):
        # Reservation creation is never a reconstruction trigger. A checkout
        # is an explicit reception action and is allowed even for web-origin
        # reservations, but only for the five reviewed booking IDs.
        if doc.get("shift_id") or not is_approved_historical_checkout(doc):
            continue
        ts = checkout_timestamp(doc)
        if ts:
            events.append({"kind": "checkout", "timestamp": ts, "doc": doc, "reason": "completed_checkout"})
    return events


def _existing_shift_map(db: Any, prop_id: int) -> dict[tuple[int, str, str], dict[str, Any]]:
    result: dict[tuple[int, str, str], dict[str, Any]] = {}
    for doc in db[RECEPTION_SHIFTS].find({"prop_id": prop_id}):
        signature = shift_signature(doc)
        if signature and signature not in result:
            result[signature] = doc
    return result


def _new_shift_document(prop_id: int, event_time: datetime, bucket: str) -> dict[str, Any]:
    start, end = bucket_window(event_time, bucket)
    now = datetime.now(timezone.utc)
    return {
        "prop_id": prop_id,
        "shift_type": bucket,
        "employee": "Historical reconciliation",
        "opened_by": "system",
        "opened_by_id": None,
        "start_time": iso(start),
        "end_time": iso(end),
        "cash_initial": 0.0,
        "cash_counted": 0.0,
        "cash_final": 0.0,
        "cash_left": 0.0,
        "cash_over_short": 0.0,
        "closing_notes": "Turno histórico reconstruido desde evidencia operacional; no sustituye un arqueo físico.",
        "total_collected": 0.0,
        "payment_breakdown": {"cash": 0, "card": 0, "transfer": 0, "other": 0, "total": 0},
        "status": "closed",
        "closed_by": "system",
        "closed_by_id": None,
        "closed_at": iso(end),
        "created_at": iso(start),
        "transactions": [],
        "payment_ids": [],
        "folio_ids": [],
        "booking_ids": [],
        "metadata": {
            "migration_id": MIGRATION_ID,
            "reconciliation": {
                "category": "historical_reconstructed",
                "evidence_bucket": f"{start.date().isoformat()}:{bucket}",
                "reconstructed_at": now,
            },
        },
    }


def _audit(db: Any, *, prop_id: int, action: str, entity_id: str, summary: str, diff: dict[str, Any], metadata: dict[str, Any]) -> None:
    db.audit_log.insert_one(
        {
            "timestamp": datetime.now(timezone.utc),
            "prop_id": prop_id,
            "entity_type": "reception_shift_reconciliation",
            "entity_id": entity_id,
            "action": action,
            "summary": summary,
            "changed_by": "system",
            "diff": safe(diff),
            "metadata": {"migration_id": MIGRATION_ID, **safe(metadata)},
        }
    )


def reconcile(*, db: Any, prop_id: int, apply: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {
        "migration_id": MIGRATION_ID,
        "database": db.name,
        "prop_id": prop_id,
        "apply": apply,
        "created_shifts": [],
        "linked_documents": [],
        "marked_demo_shifts": [],
        "cleaned_stale_booking_refs": [],
        "skipped_web_bookings": [],
        "skipped_unmatched_existing_shift_events": [],
    }
    shifts = _existing_shift_map(db, prop_id)
    events = _action_events(db, prop_id)

    # First mark probable demo records non-destructively. The original shift
    # document is preserved; only reconciliation metadata is appended.
    for shift in db[RECEPTION_SHIFTS].find({"prop_id": prop_id}):
        if not probable_demo(shift):
            continue
        item = {"shift_id": str(shift["_id"]), "employee": shift.get("employee"), "status": shift.get("status")}
        report["marked_demo_shifts"].append(item)
        if apply and shift.get("metadata", {}).get("reconciliation", {}).get("category") != "probable_test_demo":
            db[RECEPTION_SHIFTS].update_one(
                {"_id": shift["_id"]},
                {
                    "$set": {
                        "metadata.migration_id": MIGRATION_ID,
                        "metadata.reconciliation.category": "probable_test_demo",
                        "metadata.reconciliation.reason": "Label suggests test/smoke/demo; original document preserved.",
                        "metadata.reconciliation.marked_at": datetime.now(timezone.utc),
                    }
                },
            )
            _audit(db, prop_id=prop_id, action="mark", entity_id=str(shift["_id"]), summary="Turno marcado como probable smoke/demo; no eliminado.", diff={}, metadata=item)

    for event in events:
        doc = event["doc"]
        kind = event["kind"]
        if doc.get("shift_id"):
            continue
        preferred_shift_id = event.get("preferred_shift_id")
        shift = None
        if preferred_shift_id:
            # A reviewed folio must reuse the booking's existing checkout
            # shift. It is never allowed to manufacture a replacement shift.
            preferred_lookup_id = ObjectId(preferred_shift_id)
            shift = db[RECEPTION_SHIFTS].find_one({"_id": preferred_lookup_id, "prop_id": prop_id})
            if shift is None:
                report["skipped_unmatched_existing_shift_events"].append(
                    {
                        "kind": kind,
                        "document_id": safe(doc.get("_id")),
                        "preferred_shift_id": safe(preferred_shift_id),
                        "reason": "reviewed event requires an existing shift",
                    }
                )
                continue
        else:
            bucket = bucket_for_datetime(event["timestamp"])
            event_date = event["timestamp"].date().isoformat()
            signature = (prop_id, event_date, bucket)
            shift = shifts.get(signature)
            if shift is None:
                if apply:
                    result = db[RECEPTION_SHIFTS].insert_one(_new_shift_document(prop_id, event["timestamp"], bucket))
                    shift = db[RECEPTION_SHIFTS].find_one({"_id": result.inserted_id})
                    shifts[signature] = shift
                else:
                    # Keep the virtual shift in the in-memory map during dry-run;
                    # multiple actions in the same date/bucket must produce one
                    # planned shift, not one duplicate per document.
                    shift = {"_id": f"would-create:{event_date}:{bucket}", "prop_id": prop_id, "shift_type": bucket}
                    shifts[signature] = shift
                planned_shift = {"shift_id": safe(shift["_id"]), "date": event_date, "shift_type": bucket}
                if not any(item["shift_id"] == planned_shift["shift_id"] for item in report["created_shifts"]):
                    report["created_shifts"].append(planned_shift)
                if apply:
                    _audit(db, prop_id=prop_id, action="create", entity_id=str(shift["_id"]), summary=f"Turno histórico {bucket} reconstruido desde {kind}.", diff={}, metadata={"source_kind": kind, "source_id": safe(doc["_id"])})

        target = {"booking": "booking_orders", "checkout": "booking_orders", "payment": "reservation_payments", "folio": "guest_folios"}[kind]
        ref_field = {"booking": "booking_ids", "checkout": "booking_ids", "payment": "payment_ids", "folio": "folio_ids"}[kind]
        report["linked_documents"].append({"collection": target, "document_id": safe(doc["_id"]), "shift_id": safe(shift["_id"]), "kind": kind})
        if apply:
            original = doc.get("shift_id")
            db[target].update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "shift_id": shift["_id"],
                    "metadata.migration_id": MIGRATION_ID,
                    "metadata.reconciliation.original_shift_id": safe(original),
                    "metadata.reconciliation.reason": (
                        "Reviewed historical checkout/physical-cash evidence linked to an existing shift."
                        if preferred_shift_id
                        else "Reviewed historical cash-required action linked to date/shift bucket."
                    ),
                    "metadata.reconciliation.evidence_kind": kind,
                }},
            )
            db[RECEPTION_SHIFTS].update_one(
                {"_id": shift["_id"]},
                {
                    "$addToSet": {ref_field: doc["_id"]},
                    "$set": {"metadata.migration_id": MIGRATION_ID},
                },
            )
            _audit(db, prop_id=prop_id, action="link", entity_id=str(doc["_id"]), summary=f"{target} vinculado a turno histórico.", diff={"shift_id": {"old": safe(original), "new": safe(shift["_id"])}}, metadata={"collection": target, "shift_id": safe(shift["_id"]), "kind": kind})

    # Remove only stale summary references. Preserve the exact old array in
    # metadata before changing it; no business document is deleted.
    for shift in db[RECEPTION_SHIFTS].find({"prop_id": prop_id}):
        refs = list(shift.get("booking_ids") or [])
        if not refs:
            continue
        valid: list[Any] = []
        stale: list[Any] = []
        for ref in refs:
            booking = db.booking_orders.find_one(
                {"_id": ref},
                {
                    "booking_id": 1,
                    "booking_source": 1,
                    "shift_id": 1,
                    "stay_status": 1,
                    "check_out_date_actual": 1,
                    "check_out_time_actual": 1,
                },
            )
            approved_checkout_ref = bool(
                booking
                and is_approved_historical_checkout(booking)
                and (
                    booking.get("shift_id") == shift["_id"]
                    or not apply
                )
            )
            if booking is None or (
                not approved_checkout_ref
                and (
                    str(booking.get("booking_source") or "").strip().lower() in WEB_CHANNEL_SOURCES
                    or booking.get("shift_id") != shift["_id"]
                )
            ):
                stale.append(ref)
            else:
                valid.append(ref)
        if not stale:
            continue
        item = {"shift_id": str(shift["_id"]), "removed_from_summary": safe(stale), "preserved_original_count": len(refs)}
        report["cleaned_stale_booking_refs"].append(item)
        if apply:
            db[RECEPTION_SHIFTS].update_one(
                {"_id": shift["_id"]},
                {"$set": {
                    "booking_ids": valid,
                    "metadata.migration_id": MIGRATION_ID,
                    "metadata.reconciliation.original_booking_ids": safe(refs),
                    "metadata.reconciliation.cleaned_stale_booking_ids": safe(stale),
                }},
            )
            _audit(db, prop_id=prop_id, action="repair", entity_id=str(shift["_id"]), summary="Referencias de reservas web/huérfanas retiradas del resumen del turno; reserva preservada.", diff={"booking_ids": {"old": safe(refs), "new": safe(valid)}}, metadata=item)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prop-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="Persist the reviewed reconciliation; default is dry-run.")
    args = parser.parse_args(argv)
    db = get_database()
    if args.apply and db.name != "hoteldata_hub":
        raise SystemExit(f"Refusing to apply outside hoteldata_hub; resolved database={db.name!r}")
    report = reconcile(db=db, prop_id=args.prop_id, apply=args.apply)
    report_dir = Path("/app/data/reports") if Path("/app/data").exists() else Path("data/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"reception_shift_reconciliation_prop_{args.prop_id}.json"
    report_path.write_text(json.dumps(safe(report), indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({**safe(report), "report_path": str(report_path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
